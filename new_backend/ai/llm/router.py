import re
import time
import json
import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator, List, Dict, Any, Optional, Tuple

import httpx
from new_backend.ai.llm.config import load_ai_config
from new_backend.ai.llm.adapters.groq import GroqAdapter
from new_backend.ai.llm.adapters.gemini import GeminiAdapter

class DummyLogger:

    trace_id = ""

    last_completed_step = ""

    def log_external_call(self, *args, **kwargs):
        pass


def get_trace_logger():
    return DummyLogger()


def get_provider_health(provider, model):
    return {
        "current_health_score": 100,
        "success_count": 0,
        "failure_count": 0,
        "average_latency": 0,
        "rate_limit_count": 0,
        "cooldown_until": None,
    }


def record_success(*args, **kwargs):
    pass


def record_failure(*args, **kwargs):
    pass
def parse_retry_after(exception: Exception) -> Optional[int]:
    if isinstance(exception, httpx.HTTPStatusError):
        retry_after = exception.response.headers.get("Retry-After")
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                pass
        body = exception.response.text
        match = re.search(r"try again in (\d+\.?\d*)s", body)
        if match:
            try:
                return int(float(match.group(1)))
            except ValueError:
                pass
    return None

def optimize_system_prompt(system_prompt: str) -> str:
    if not system_prompt:
        return system_prompt
    try:
        matches = re.findall(r"(Zoho CRM \w+:\n)(\[[\s\S]*?\])", system_prompt)
        for prefix, json_str in matches:
            try:
                data = json.loads(json_str)
                if isinstance(data, list) and len(data) > 3:
                    truncated = data[:3]
                    for rec in truncated:
                        if isinstance(rec, dict):
                            for k in list(rec.keys()):
                                if k in ["Description", "Modified_Time", "Created_Time", "$editable", "$orchestration"]:
                                    rec.pop(k, None)
                    compressed_json = json.dumps(truncated, indent=2)
                    system_prompt = system_prompt.replace(json_str, compressed_json)
            except Exception:
                pass
    except Exception:
        pass

    if len(system_prompt) > 2000:
        system_prompt = re.sub(
            r"VISUALIZATION TYPES:\n[\s\S]*?UNIFIED RESPONSE FORMAT:",
            "VISUALIZATION TYPES:\ntable, bar, line, pie, funnel, sankey, heatmap, waterfall, scatter, kpi_cards\n\nUNIFIED RESPONSE FORMAT:",
            system_prompt
        )
    return system_prompt

class AIRouter:
    def __init__(self):
        self.config = load_ai_config()
        self.models_config = self.config.get("models", {})
        self.tasks_config = self.config.get("tasks", {})
        self.providers_config = self.config.get("providers", {})
        
    def _get_api_key(self, provider: str, passed_api_keys: Optional[Dict[str, str]] = None) -> str:
        # 1. Check explicitly passed api_keys dict (takes highest priority)
        if passed_api_keys and provider in passed_api_keys:
            key = passed_api_keys[provider]
            if key:
                return key

        # 2. Check the per-request user config loaded from the database (via ContextVar)
        user_cfg = {}
        if user_cfg:
            key_map = {
                "groq": user_cfg.get("groq_api_key") or "",
                "gemini": user_cfg.get("gemini_api_key") or "",
            }
            key = key_map.get(provider, "")
            if key:
                return key

        return ""

    def _get_adapter(self, provider: str, model: str, api_key: str) -> Any:
        model_cfg = self.models_config.get(model, {})
        model_cfg_copy = dict(model_cfg)
        model_cfg_copy["base_url"] = self.providers_config.get(provider, {}).get("base_url", "")
        
        if provider == "groq":
            return GroqAdapter(model, model_cfg_copy, api_key)
        elif provider == "gemini":
            return GeminiAdapter(model, model_cfg_copy, api_key)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _get_ranked_models(self, task_type: str, estimated_tokens: int = 0) -> List[Tuple[str, str, Dict[str, Any]]]:
        task_cfg = self.tasks_config.get(task_type, {})
        model_chain = task_cfg.get("model_chain", [])
        required_caps = task_cfg.get("required_capabilities", [])
        
        candidates = []
        cooldown_candidates = []
        
        for model in model_chain:
            model_cfg = self.models_config.get(model, {})
            provider = model_cfg.get("provider")
            if not provider:
                continue
            
            # Validate required capabilities
            capabilities_met = True
            for cap in required_caps:
                if not model_cfg.get(cap, False):
                    capabilities_met = False
                    break
            if not capabilities_met:
                continue
                
            # Fetch health status from SQLite
            health = get_provider_health(provider, model)
            
            # Check if model is in cooldown
            in_cooldown = False
            cooldown_until_str = health.get("cooldown_until")
            if cooldown_until_str:
                try:
                    clean_ts = cooldown_until_str.rstrip("Z")
                    cooldown_until = datetime.fromisoformat(clean_ts)
                    if cooldown_until > datetime.utcnow():
                        in_cooldown = True
                except Exception:
                    pass
            
            candidate_tuple = (provider, model, health)
            if in_cooldown:
                cooldown_candidates.append(candidate_tuple)
            else:
                candidates.append(candidate_tuple)
                
        # Fallback to cooldown list if all configured candidate models are in cooldown
        if not candidates:
            candidates = cooldown_candidates
            
        def get_model_score(item):
            provider, model, health = item
            health_score = health.get("current_health_score", 100.0)
            
            s_count = health.get("success_count", 0)
            f_count = health.get("failure_count", 0)
            total_calls = s_count + f_count
            success_rate = s_count / total_calls if total_calls > 0 else 1.0
            success_bonus = success_rate * 20.0
            
            average_latency = health.get("average_latency", 0.0)
            latency_penalty = min(20.0, average_latency * 2.0) if average_latency > 0 else 0.0
            
            rate_limit_count = health.get("rate_limit_count", 0)
            rl_penalty = min(15.0, rate_limit_count * 3.0)
            
            preferred_models = []
            if estimated_tokens < 500:
                preferred_models = ["gemini-2.5-flash-lite"]
            elif 500 <= estimated_tokens <= 3000:
                preferred_models = ["gemini-2.5-flash", "groq/compound-mini"]
            elif 3000 < estimated_tokens <= 10000:
                preferred_models = [
                    "llama-3.3-70b-versatile",
                    "llama-3.1-8b-instant"
                ]
            else:
                preferred_models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
                
            suitability_bonus = 30.0 if model in preferred_models else 0.0
            
            try:
                config_priority = model_chain.index(model)
            except ValueError:
                config_priority = 999
            priority_penalty = config_priority * 1.0
            
            return health_score + success_bonus + suitability_bonus - latency_penalty - rl_penalty - priority_penalty

        def sort_key(item):
            return -get_model_score(item)

        candidates.sort(key=sort_key)
        return candidates

    async def _execute_with_failover(
        self,
        task_type: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        api_keys: Optional[Dict[str, str]] = None,
        stream_mode: bool = False
    ) -> Any:
        logger = get_trace_logger()
        
        task_cfg = self.tasks_config.get(task_type, {})
        model_chain = task_cfg.get("model_chain", [])
        required_caps = task_cfg.get("required_capabilities", [])
        
        # Build attempt logs
        routing_log = []
        task_display = "response_generation" if task_type == "general_crm" else task_type
        
        # Calculate initial estimated tokens
        total_chars = len(prompt)
        if system_prompt:
            total_chars += len(system_prompt)
        if messages:
            for msg in messages:
                total_chars += len(msg.get("content") or msg.get("message") or "")
        estimated_tokens = total_chars // 4

        opt_applied = "No"
        # Pre-optimize if estimated tokens > 10000
        if estimated_tokens > 10000:
            print(f"[AIRouter Pre-Optimization] Prompt size {estimated_tokens} exceeds 10,000 tokens. Running optimization sequence.", flush=True)
            system_prompt = optimize_system_prompt(system_prompt)
            if messages:
                if len(messages) > 2:
                    messages = [messages[0]] + messages[-1:]
            opt_applied = "Yes"
            
            # Recalculate estimated tokens
            total_chars = len(prompt)
            if system_prompt:
                total_chars += len(system_prompt)
            if messages:
                for msg in messages:
                    total_chars += len(msg.get("content") or msg.get("message") or "")
            estimated_tokens = total_chars // 4

        # Check all models in task's model chain
        candidates = []
        skipped_reasons = {}
        
        for model in model_chain:
            model_cfg = self.models_config.get(model, {})
            provider = model_cfg.get("provider")
            if not provider:
                continue
            
            # Check capabilities
            capabilities_met = True
            for cap in required_caps:
                if not model_cfg.get(cap, False):
                    capabilities_met = False
                    break
            if not capabilities_met:
                skipped_reasons[model] = "Capability mismatch"
                continue
                
            # Check API key
            api_key = self._get_api_key(provider, api_keys)
            if not api_key:
                skipped_reasons[model] = "No API key"
                continue
                
            # Check cooldown
            health = get_provider_health(provider, model)
            in_cooldown = False
            cooldown_until_str = health.get("cooldown_until")
            if cooldown_until_str:
                try:
                    clean_ts = cooldown_until_str.rstrip("Z")
                    cooldown_until = datetime.fromisoformat(clean_ts)
                    if cooldown_until > datetime.utcnow():
                        in_cooldown = True
                except Exception:
                    pass
            candidates.append((provider, model, health, in_cooldown))
            
        # Determine if there's any non-cooldown candidate
        has_non_cooldown = any(not item[3] for item in candidates)
        
        models_to_attempt = []
        for provider, model, health, in_cooldown in candidates:
            if in_cooldown and has_non_cooldown:
                skipped_reasons[model] = "Provider in cooldown"
            else:
                models_to_attempt.append((provider, model, health))
                
        def get_model_score(item):
            provider, model, health = item
            health_score = health.get("current_health_score", 100.0)
            
            s_count = health.get("success_count", 0)
            f_count = health.get("failure_count", 0)
            total_calls = s_count + f_count
            success_rate = s_count / total_calls if total_calls > 0 else 1.0
            success_bonus = success_rate * 20.0
            
            average_latency = health.get("average_latency", 0.0)
            latency_penalty = min(20.0, average_latency * 2.0) if average_latency > 0 else 0.0
            
            rate_limit_count = health.get("rate_limit_count", 0)
            rl_penalty = min(15.0, rate_limit_count * 3.0)
            
            preferred_models = []
            if estimated_tokens < 500:
                preferred_models = ["gemini-2.5-flash-lite"]
            elif 500 <= estimated_tokens <= 3000:
                preferred_models = ["gemini-2.5-flash", "groq/compound-mini"]
            elif 3000 < estimated_tokens <= 10000:
                preferred_models = ["groq/compound", "llama-4-scout-17b-16e-instruct"]
            else:
                preferred_models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
                
            suitability_bonus = 30.0 if model in preferred_models else 0.0
            
            try:
                config_priority = model_chain.index(model)
            except ValueError:
                config_priority = 999
            priority_penalty = config_priority * 1.0
            
            return health_score + success_bonus + suitability_bonus - latency_penalty - rl_penalty - priority_penalty

        def sort_key(item):
            return -get_model_score(item)
            
        models_to_attempt.sort(key=sort_key)
        
        # Helper for printing names
        def format_model_name(m: str) -> str:
            if m == "gemini-2.5-flash":
                return "Gemini 2.5 Flash"
            elif m == "gemini-2.5-flash-lite":
                return "Gemini 2.5 Flash Lite"
            elif m == "llama-3.3-70b-versatile":
                return "Groq llama-3.3-70b-versatile"
            elif m == "llama-3.1-8b-instant":
                return "Groq llama-3.1-8b-instant"
            return m

        def format_filtered_name(m: str) -> str:
            if m == "gemini-2.5-flash":
                return "Gemini 2.5 Flash"
            elif m == "gemini-2.5-flash-lite":
                return "Gemini 2.5 Flash Lite"
            elif m == "llama-3.3-70b-versatile":
                return "Groq"
            elif m == "llama-3.1-8b-instant":
                return "Groq Instant"
            return m
            
        # --- STEP 2: PRINT ROUTER DECISION TREE ---
        print(f"\nTask: {task_display}\n", flush=True)
        print("Configured Chain:", flush=True)
        for i, model_item in enumerate(model_chain):
            print(f"{i+1}. {format_model_name(model_item)}", flush=True)
            
        print("\nFiltered:", flush=True)
        for model_item in model_chain:
            display_name = format_filtered_name(model_item)
            if model_item in skipped_reasons:
                print(f"{display_name} -> Filtered ({skipped_reasons[model_item]})", flush=True)
            else:
                print(f"{display_name} -> Available", flush=True)
                
        print("\nSelected:", flush=True)
        if models_to_attempt:
            print(f"{format_model_name(models_to_attempt[0][1])}\n", flush=True)
        else:
            print("None\n", flush=True)
            
        # Log skipped models
        for model_item in model_chain:
            if model_item in skipped_reasons:
                model_cfg = self.models_config.get(model_item, {})
                provider = model_cfg.get("provider", "")
                provider_display = "Gemini" if provider == "gemini" else ("Groq" if provider == "groq" else provider.title())
                reason = skipped_reasons[model_item]
                print(f"Skipping {provider_display}\nReason: {reason}\n", flush=True)
        
        if not candidates and not skipped_reasons:
            raise ValueError(f"No configured or capability-compatible models available for task: {task_type}")
            
        if not models_to_attempt:
            raise ValueError(
                "No AI provider API keys are configured. "
                "Please go to Settings and add at least one AI provider key "
                "(Groq API Key or Gemini API Key) to use the chatbot."
            )
            
        last_exception = None
        final_result = None
        success = False
        
        retry_count = 0
        attempt_results = {}
        
        for attempt_idx, (provider, model, health) in enumerate(models_to_attempt):
            api_key = self._get_api_key(provider, api_keys)
            api_key_status = "FOUND" if api_key else "NOT FOUND"
            attempt_number = attempt_idx + 1
            provider_display = "Gemini" if provider == "gemini" else ("Groq" if provider == "groq" else provider.title())
            
            # Find cooldown status for log
            in_cooldown = False
            cooldown_until_str = health.get("cooldown_until")
            if cooldown_until_str:
                try:
                    clean_ts = cooldown_until_str.rstrip("Z")
                    cooldown_until = datetime.fromisoformat(clean_ts)
                    if cooldown_until > datetime.utcnow():
                        in_cooldown = True
                except Exception:
                    pass
            
            call_start = time.time()
            
            logger.last_completed_step = f"AI Router: Calling {provider}/{model} (Attempt {attempt_number})"
            adapter = self._get_adapter(provider, model, api_key)
            
            try:
                if stream_mode:
                    stream_gen = adapter.stream(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    
                    try:
                        first_chunk = await asyncio.wait_for(stream_gen.__anext__(), timeout=10.0)
                    except StopAsyncIteration:
                        first_chunk = ""
                        
                    async def stream_wrapper(initial_chunk, generator):
                        if initial_chunk:
                            yield initial_chunk
                        async for chunk in generator:
                            yield chunk
                            
                    duration = time.time() - call_start
                    record_success(provider, model, duration)
                    
                    logger.log_external_call(
                        component="LLM",
                        start_time=call_start,
                        payload={
                            "trace_id": logger.trace_id,
                            "task_type": task_type,
                            "selected_provider": provider,
                            "selected_model": model,
                            "attempt_number": attempt_number,
                            "retry_count": retry_count,
                            "prompt_optimization_applied": opt_applied,
                            "estimated_prompt_size": estimated_tokens,
                        },
                        status="SUCCESS",
                        response={
                            "response_time": f"{duration:.3f}s",
                            "final_provider_used": provider
                        }
                    )
                    
                    success = True
                    final_result = stream_wrapper(first_chunk, stream_gen)
                    
                    # --- STEP 1: PRINT COMPLETE LOG FOR SUCCESS ---
                    print(f"\nAttempt {attempt_number}\n"
                          f"Provider: {provider_display}\n"
                          f"Model: {model}\n"
                          f"API Key: {api_key_status}\n"
                          f"Health: {int(health.get('current_health_score', 100.0))}\n"
                          f"Cooldown: {in_cooldown}\n"
                          f"Capabilities: OK\n"
                          f"Prompt Size: {estimated_tokens} tokens\n"
                          f"Optimization Applied: {opt_applied}\n"
                          f"Retry Count: {retry_count}\n"
                          f"Response Time: {duration:.3f}s\n"
                          f"HTTP Status: 200\n"
                          f"Result: SUCCESS\n", flush=True)
                    break
                    
                else:
                    response_text = await adapter.generate(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    if (
                        task_type == "crud_extraction"
                        and response_text.count("{") > response_text.count("}")
                    ):
                        print("[AIRouter] Incomplete JSON. Trying next provider.")
                        continue
                    
                    duration = time.time() - call_start
                    record_success(provider, model, duration)
                    
                    logger.log_external_call(
                        component="LLM",
                        start_time=call_start,
                        payload={
                            "trace_id": logger.trace_id,
                            "task_type": task_type,
                            "selected_provider": provider,
                            "selected_model": model,
                            "attempt_number": attempt_number,
                            "retry_count": retry_count,
                            "prompt_optimization_applied": opt_applied,
                            "estimated_prompt_size": estimated_tokens,
                        },
                        status="SUCCESS",
                        response={
                            "response_time": f"{duration:.3f}s",
                            "estimated_response_size": len(response_text),
                            "final_provider_used": provider
                        }
                    )
                    
                    success = True
                    final_result = response_text
                    
                    # --- STEP 1: PRINT COMPLETE LOG FOR SUCCESS ---
                    print(f"\nAttempt {attempt_number}\n"
                          f"Provider: {provider_display}\n"
                          f"Model: {model}\n"
                          f"API Key: {api_key_status}\n"
                          f"Health: {int(health.get('current_health_score', 100.0))}\n"
                          f"Cooldown: {in_cooldown}\n"
                          f"Capabilities: OK\n"
                          f"Prompt Size: {estimated_tokens} tokens\n"
                          f"Optimization Applied: {opt_applied}\n"
                          f"Retry Count: {retry_count}\n"
                          f"Response Time: {duration:.3f}s\n"
                          f"HTTP Status: 200\n"
                          f"Result: SUCCESS\n", flush=True)
                    break
                    
            except Exception as e:
                duration = time.time() - call_start
                is_rate_limit = False
                cooldown_sec = None
                
                result_status = "FAILED"
                http_status = "N/A"
                if isinstance(e, httpx.HTTPStatusError):
                    http_status = e.response.status_code
                    if e.response.status_code == 429:
                        is_rate_limit = True
                        cooldown_sec = parse_retry_after(e)
                        result_status = "429 Rate Limit"
                    elif e.response.status_code == 400:
                        result_status = "400 Invalid API Key"
                    elif e.response.status_code == 413:
                        result_status = "413 Prompt Too Large"
                    else:
                        result_status = f"FAILED ({e.response.status_code})"
                elif "429" in str(e) or "limit" in str(e).lower():
                    is_rate_limit = True
                    result_status = "429 Rate Limit"
                    http_status = 429
                elif "400" in str(e):
                    result_status = "400 Invalid API Key"
                    http_status = 400
                elif "413" in str(e) or "too large" in str(e).lower():
                    result_status = "413 Prompt Too Large"
                    http_status = 413
                else:
                    result_status = f"FAILED ({type(e).__name__})"
                    
                record_failure(provider, model, is_rate_limit=is_rate_limit, cooldown_seconds=cooldown_sec)
                
                logger.log_external_call(
                    component="LLM",
                    start_time=call_start,
                    payload={
                        "trace_id": logger.trace_id,
                        "task_type": task_type,
                        "selected_provider": provider,
                        "selected_model": model,
                        "attempt_number": attempt_number,
                        "retry_count": retry_count,
                        "prompt_optimization_applied": opt_applied,
                        "estimated_prompt_size": estimated_tokens,
                    },
                    status="FAILED",
                    response={
                        "response_time": f"{duration:.3f}s",
                        "failover_reason": str(e),
                    },
                    exception_type=type(e).__name__
                )
                
                is_context_limit = (http_status == 413) or any(x in str(e).lower() for x in ["413", "token limit", "context length", "too large", "limit exceeded"])
                
                retry_succeeded = False
                if is_context_limit and opt_applied == "No":
                    opt_applied = "Yes"
                    retry_count += 1
                    
                    optimized_sys = optimize_system_prompt(system_prompt)
                    optimized_messages = None
                    if messages:
                        if len(messages) > 2:
                            optimized_messages = [messages[0]] + messages[-1:]
                        else:
                            optimized_messages = messages
                        
                    print(f"[AIRouter Retry] Retrying optimized payload on model {model} due to token/context limit.", flush=True)
                    
                    try:
                        retry_start = time.time()
                        if stream_mode:
                            stream_gen = adapter.stream(
                                prompt=prompt,
                                system_prompt=optimized_sys,
                                messages=optimized_messages,
                                temperature=temperature,
                                max_tokens=max_tokens
                            )
                            try:
                                first_chunk = await asyncio.wait_for(stream_gen.__anext__(), timeout=10.0)
                            except StopAsyncIteration:
                                first_chunk = ""
                                
                            async def stream_wrapper(initial_chunk, generator):
                                if initial_chunk:
                                    yield initial_chunk
                                async for chunk in generator:
                                    yield chunk
                                    
                            duration = time.time() - retry_start
                            record_success(provider, model, duration)
                            success = True
                            final_result = stream_wrapper(first_chunk, stream_gen)
                            retry_succeeded = True
                        else:
                            response_text = await adapter.generate(
                                prompt=prompt,
                                system_prompt=optimized_sys,
                                messages=optimized_messages,
                                temperature=temperature,
                                max_tokens=max_tokens
                            )
                            duration = time.time() - retry_start
                            record_success(provider, model, duration)
                            success = True
                            final_result = response_text
                            retry_succeeded = True
                            
                        if retry_succeeded:
                            print(f"\nAttempt {attempt_number} (Retry Succeeded)\n"
                                  f"Provider: {provider_display}\n"
                                  f"Model: {model}\n"
                                  f"API Key: {api_key_status}\n"
                                  f"Health: {int(health.get('current_health_score', 100.0))}\n"
                                  f"Cooldown: {in_cooldown}\n"
                                  f"Capabilities: OK\n"
                                  f"Prompt Size: {estimated_tokens} tokens\n"
                                  f"Optimization Applied: Yes\n"
                                  f"Retry Count: {retry_count}\n"
                                  f"Response Time: {duration:.3f}s\n"
                                  f"HTTP Status: 200\n"
                                  f"Result: SUCCESS\n", flush=True)
                            break
                    except Exception as retry_err:
                        last_exception = retry_err
                        if isinstance(retry_err, httpx.HTTPStatusError):
                            http_status = retry_err.response.status_code
                            if retry_err.response.status_code == 429:
                                result_status = "429 Rate Limit"
                            elif retry_err.response.status_code == 400:
                                result_status = "400 Invalid API Key"
                            elif retry_err.response.status_code == 413:
                                result_status = "413 Prompt Too Large"
                            else:
                                result_status = f"FAILED ({retry_err.response.status_code})"
                        else:
                            result_status = f"FAILED ({type(retry_err).__name__})"
                else:
                    last_exception = e
                    
                if not retry_succeeded:
                    attempt_results[model] = result_status
                    print(f"\nAttempt {attempt_number}\n"
                          f"Provider: {provider_display}\n"
                          f"Model: {model}\n"
                          f"API Key: {api_key_status}\n"
                          f"Health: {int(health.get('current_health_score', 100.0))}\n"
                          f"Cooldown: {in_cooldown}\n"
                          f"Capabilities: OK\n"
                          f"Prompt Size: {estimated_tokens} tokens\n"
                          f"Optimization Applied: {opt_applied}\n"
                          f"Retry Count: {retry_count}\n"
                          f"HTTP Status: {http_status}\n"
                          f"Exception Message: {str(last_exception)}\n"
                          f"Failover Reason: {result_status}\n"
                          f"Result: {result_status}\n", flush=True)
                    
        if not success:
            summary = []
            summary.append("\nProvider Summary\n")
            for model_item in model_chain:
                model_cfg = self.models_config.get(model_item, {})
                provider = model_cfg.get("provider", "")
                display_name = format_filtered_name(model_item)
                
                if model_item in skipped_reasons:
                    summary.append(f"{display_name}\nSkipped - Reason: {skipped_reasons[model_item]}\n")
                elif model_item in attempt_results:
                    summary.append(f"{display_name}\n{attempt_results[model_item]}\n")
                else:
                    summary.append(f"{display_name}\nNot attempted\n")
                    
            summary.append("\nFinal Decision\nAll configured providers failed.\n")
            print("\n".join(summary), flush=True)
            
            raise last_exception or RuntimeError("All model choices failed in AIRouter chain.")
            
        return final_result

    # ==============================================================================
    # TASK-SPECIFIC INTERFACES
    # ==============================================================================
    
    async def classify(self, prompt: str, system_prompt: str = None, messages: list = None, api_keys: Optional[Dict[str, str]] = None) -> dict:
        res_text = await self._execute_with_failover(
            task_type="intent_classification",
            prompt=prompt,
            system_prompt=system_prompt,
            messages=messages,
            temperature=0.0,
            max_tokens=150,
            api_keys=api_keys,
            stream_mode=False
        )
        try:
            cleaned = re.sub(r"^```json\s*|\s*```$", "", res_text.strip(), flags=re.IGNORECASE)
            return json.loads(cleaned)
        except Exception as e:
            print(f"[AIRouter Classify Parsing Error] Failed to parse: {res_text}. Error: {e}")
            match = re.search(r"\{[\s\S]*\}", res_text)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
            return {"intent": "general_chat", "query_term": None}

    async def extract_json(self, prompt: str, system_prompt: str = None, messages: list = None, api_keys: Optional[Dict[str, str]] = None) -> dict:
        res_text = await self._execute_with_failover(
            task_type="crud_extraction",
            prompt=prompt,
            system_prompt=system_prompt,
            messages=messages,
            temperature=0.0,
            max_tokens=500,
            api_keys=api_keys,
            stream_mode=False
        )
        try:
            cleaned = re.sub(r"^```json\s*|\s*```$", "", res_text.strip(), flags=re.IGNORECASE)
            return json.loads(cleaned)
        except Exception:
            match = re.search(r"\{[\s\S]*\}", res_text)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
            print("\n[AIRouter] Invalid JSON received.")
            print(res_text)

            return {}

    async def generate_response(self, prompt: str, system_prompt: str = None, messages: list = None, temperature: float = 0.0, api_keys: Optional[Dict[str, str]] = None) -> str:
        return await self._execute_with_failover(
            task_type="general_crm",
            prompt=prompt,
            system_prompt=system_prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=1024,
            api_keys=api_keys,
            stream_mode=False
        )

    async def stream_response(
        self,
        prompt: str,
        system_prompt: str = None,
        messages: list = None,
        temperature: float = 0.0,
        api_keys: Optional[Dict[str, str]] = None,
        task_type: str = "general_crm"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        logger = get_trace_logger()
        task_cfg = self.tasks_config.get(task_type, {})
        model_chain = task_cfg.get("model_chain", [])
        required_caps = task_cfg.get("required_capabilities", [])
        
        # Calculate estimated tokens
        total_chars = len(prompt)
        if system_prompt:
            total_chars += len(system_prompt)
        if messages:
            for msg in messages:
                total_chars += len(msg.get("content") or msg.get("message") or "")
        estimated_tokens = total_chars // 4

        opt_applied = "No"
        # Optimize system prompt if too large
        if estimated_tokens > 10000:
            system_prompt = optimize_system_prompt(system_prompt)
            if messages and len(messages) > 2:
                messages = [messages[0]] + messages[-1:]
            opt_applied = "Yes"
            
            # Recalculate
            total_chars = len(prompt)
            if system_prompt:
                total_chars += len(system_prompt)
            if messages:
                for msg in messages:
                    total_chars += len(msg.get("content") or msg.get("message") or "")
            estimated_tokens = total_chars // 4

        candidates = []
        skipped_reasons = {}
        
        for model in model_chain:
            model_cfg = self.models_config.get(model, {})
            provider = model_cfg.get("provider")
            if not provider:
                continue
            
            # Check capabilities
            capabilities_met = True
            for cap in required_caps:
                if not model_cfg.get(cap, False):
                    capabilities_met = False
                    break
            if not capabilities_met:
                skipped_reasons[model] = "Capability mismatch"
                continue
                
            # Check API key
            api_key = self._get_api_key(provider, api_keys)
            if not api_key:
                skipped_reasons[model] = "No API key"
                continue
                
            # Check cooldown
            health = get_provider_health(provider, model)
            in_cooldown = False
            cooldown_until_str = health.get("cooldown_until")
            if cooldown_until_str:
                try:
                    clean_ts = cooldown_until_str.rstrip("Z")
                    cooldown_until = datetime.fromisoformat(clean_ts)
                    if cooldown_until > datetime.utcnow():
                        in_cooldown = True
                except Exception:
                    pass
            candidates.append((provider, model, health, in_cooldown))
            
        has_non_cooldown = any(not item[3] for item in candidates)
        
        models_to_attempt = []
        for provider, model, health, in_cooldown in candidates:
            if in_cooldown and has_non_cooldown:
                skipped_reasons[model] = "Provider in cooldown"
            else:
                models_to_attempt.append((provider, model, health))
                
        # Sorting
        def get_model_score(item):
            provider, model, health = item
            health_score = health.get("current_health_score", 100.0)
            
            s_count = health.get("success_count", 0)
            f_count = health.get("failure_count", 0)
            total_calls = s_count + f_count
            success_rate = s_count / total_calls if total_calls > 0 else 1.0
            success_bonus = success_rate * 20.0
            
            average_latency = health.get("average_latency", 0.0)
            latency_penalty = min(20.0, average_latency * 2.0) if average_latency > 0 else 0.0
            
            rate_limit_count = health.get("rate_limit_count", 0)
            rl_penalty = min(15.0, rate_limit_count * 3.0)
            
            preferred_models = ["gemini-2.5-flash-lite"] if estimated_tokens < 500 else (
                ["gemini-2.5-flash", "groq/compound-mini"] if estimated_tokens <= 3000 else (
                    ["groq/compound", "llama-4-scout-17b-16e-instruct"] if estimated_tokens <= 10000 else
                    ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
                )
            )
            suitability_bonus = 30.0 if model in preferred_models else 0.0
            
            try:
                config_priority = model_chain.index(model)
            except ValueError:
                config_priority = 999
            priority_penalty = config_priority * 1.0
            
            return health_score + success_bonus + suitability_bonus - latency_penalty - rl_penalty - priority_penalty

        models_to_attempt.sort(key=lambda x: -get_model_score(x))
        
        if not models_to_attempt:
            raise ValueError("No AI provider API keys are configured. Please check your settings.")
            
        success = False
        last_exception = None
        
        for attempt_idx, (provider, model, health) in enumerate(models_to_attempt):
            api_key = self._get_api_key(provider, api_keys)
            attempt_number = attempt_idx + 1
            provider_display = "Gemini" if provider == "gemini" else ("Groq" if provider == "groq" else provider.title())
            
            # Emit user-facing generic status updates
            if attempt_number == 1:
                yield {"event": "status", "message": "Trying AI model..."}
            else:
                yield {"event": "status", "message": "Trying another AI model..."}
                
            # Log internally
            print(f"[AIRouter Stream Attempt {attempt_number}] Provider: {provider_display}, Model: {model}", flush=True)
            
            call_start = time.time()
            adapter = self._get_adapter(provider, model, api_key)
            
            try:
                stream_gen = adapter.stream(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=1024
                )
                
                try:
                    first_chunk = await asyncio.wait_for(stream_gen.__anext__(), timeout=10.0)
                except StopAsyncIteration:
                    first_chunk = ""
                    
                # Success! Yield the almost done status
                yield {"event": "status", "message": "Almost done..."}
                
                # Emit chunks
                if first_chunk:
                    yield {"event": "chunk", "chunk": first_chunk}
                async for chunk in stream_gen:
                    yield {"event": "chunk", "chunk": chunk}
                    
                duration = time.time() - call_start
                record_success(provider, model, duration)
                success = True
                
                # Internal success log
                print(f"[AIRouter Stream Success] Model: {model}, Duration: {duration:.3f}s", flush=True)
                break
                
            except Exception as e:
                duration = time.time() - call_start
                is_rate_limit = "429" in str(e) or "limit" in str(e).lower()
                record_failure(provider, model, is_rate_limit=is_rate_limit)
                last_exception = e
                
                # Internal failure log
                print(f"[AIRouter Stream Failed] Model: {model}, Duration: {duration:.3f}s, Reason: {str(e)}", flush=True)
                
        if not success and last_exception:
            raise last_exception

    async def summarize(self, prompt: str, system_prompt: str = None, messages: list = None, api_keys: Optional[Dict[str, str]] = None) -> str:
        return await self._execute_with_failover(
            task_type="summaries",
            prompt=prompt,
            system_prompt=system_prompt,
            messages=messages,
            temperature=0.0,
            max_tokens=1024,
            api_keys=api_keys,
            stream_mode=False
        )
    async def analytics_interpretation(
        self,
        prompt: str,
        system_prompt: str = None,
        messages: list = None,
        api_keys: Optional[Dict[str, str]] = None,
    ) -> dict:

        res_text = await self._execute_with_failover(
            task_type="analytics_interpretation",
            prompt=prompt,
            system_prompt=system_prompt,
            messages=messages,
            temperature=0.0,
            max_tokens=400,
            api_keys=api_keys,
            stream_mode=False,
        )

        try:
            cleaned = re.sub(
                r"^```json\s*|\s*```$",
                "",
                res_text.strip(),
                flags=re.IGNORECASE,
            )

            return json.loads(cleaned)

        except Exception:

            match = re.search(r"\{[\s\S]*\}", res_text)

            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass

            return {}

    async def generate_report(self, prompt: str, system_prompt: str = None, messages: list = None, api_keys: Optional[Dict[str, str]] = None) -> str:
        return await self._execute_with_failover(
            task_type="long_reports",
            prompt=prompt,
            system_prompt=system_prompt,
            messages=messages,
            temperature=0.0,
            max_tokens=2048,
            api_keys=api_keys,
            stream_mode=False
        )

_ai_router_instance = None

def get_ai_router() -> AIRouter:
    global _ai_router_instance
    if _ai_router_instance is None:
        _ai_router_instance = AIRouter()
    return _ai_router_instance
