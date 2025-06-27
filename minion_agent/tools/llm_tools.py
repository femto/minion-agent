from typing import Optional

def llm_text_generate(
    prompt: str,
    model: str = "gpt-3.5-turbo",
    system_prompt: str = "You are a helpful assistant.",
    temperature: float = 0.7,
    top_p: float = 1.0,
) -> str:
    """
    Generate text using a large language model (LLM).
    Args:
        prompt: The user prompt or question.
        model: The LLM model name (default: gpt-3.5-turbo).
        system_prompt: System prompt for LLM (default: assistant role).
        temperature: Sampling temperature.
        top_p: Nucleus sampling parameter.
    Returns:
        Generated text as a string.
    """
    # TODO: Replace with your LLM backend (OpenAI, Qwen, etc.)
    try:
        import openai
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            top_p=top_p,
        )
        return response["choices"][0]["message"]["content"]
    except ImportError:
        raise RuntimeError("openai package not installed. Please install openai or implement your own backend.")
    except Exception as e:
        raise RuntimeError(f"LLM text generation failed: {e}")

def llm_image_generate(
    prompt: str,
    model: str = "dall-e-3",
    size: str = "1024x1024",
    style: str = "vivid",
    seed: int = 0,
) -> str:
    """
    Generate an image using an LLM-based image model.
    Args:
        prompt: The image description prompt.
        model: The image model name (default: dall-e-3).
        size: Image size (e.g., '1024x1024').
        style: Image style (e.g., 'vivid', 'natural').
        seed: Random seed for reproducibility (if supported).
    Returns:
        Base64-encoded image string.
    """
    # TODO: Replace with your image generation backend (OpenAI, Stable Diffusion, etc.)
    try:
        import openai
        response = openai.Image.create(
            prompt=prompt,
            model=model,
            n=1,
            size=size,
            response_format="b64_json",
            user=None,
        )
        return response["data"][0]["b64_json"]
    except ImportError:
        raise RuntimeError("openai package not installed. Please install openai or implement your own backend.")
    except Exception as e:
        raise RuntimeError(f"LLM image generation failed: {e}")

def plan(task: str, context: Optional[str] = None) -> str:
    """
    Generate a step-by-step plan for the given task or goal using LLM.
    Args:
        task: The task or goal to plan for.
        context: Optional additional context or constraints.
    Returns:
        A markdown-formatted plan as a string.
    """
    prompt = f"请为如下任务生成详细的分步计划：\n任务：{task}\n" + (f"上下文：{context}\n" if context else "")
    return llm_text_generate(prompt)

def reflection(progress: str, goal: str) -> str:
    """
    Reflect on the current progress and suggest improvements using LLM.
    Args:
        progress: The current progress or output.
        goal: The original goal or requirement.
    Returns:
        Reflection and suggestions as a string.
    """
    prompt = f"请对以下进展进行反思，并给出改进建议：\n进展：{progress}\n目标：{goal}"
    return llm_text_generate(prompt)

def check(result: str, goal: str) -> str:
    """
    Check the quality or correctness of a result against a goal using LLM.
    Args:
        result: The result or output to check.
        goal: The original goal or requirement.
    Returns:
        Check feedback as a string.
    """
    prompt = f"请检查以下结果是否满足目标，并指出不足：\n结果：{result}\n目标：{goal}"
    return llm_text_generate(prompt)

def improve(result: str, feedback: Optional[str] = None, goal: Optional[str] = None) -> str:
    """
    Improve a given result based on feedback or a goal using LLM.
    Args:
        result: The result or output to improve.
        feedback: Optional feedback or suggestions.
        goal: Optional original goal or requirement.
    Returns:
        Improved result as a string.
    """
    prompt = f"请根据以下反馈或目标改进结果：\n结果：{result}\n" + (f"反馈：{feedback}\n" if feedback else "") + (f"目标：{goal}\n" if goal else "")
    return llm_text_generate(prompt) 