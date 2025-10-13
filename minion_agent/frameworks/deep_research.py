import os
from typing import Optional, Any, List

from minion_agent.config import AgentFramework, AgentConfig
from minion_agent.frameworks.deep_research_llms import asingle_shot_llm_call
from minion_agent.frameworks.minion_agent import MinionAgent
from minion_agent.frameworks.deep_research_types import (
    ResearchPlan,
    SourceList,
    DeepResearchResult,
    DeepResearchResults,
    UserCommunication, atavily_search_results
)
from loguru import logger

import asyncio
import hashlib
import json
import os
import pickle
import re
import sys
import select
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, List

import yaml
from dotenv import load_dotenv
from filelock import FileLock

try:
    deep_research_available = True
except ImportError:
    deep_research_available = None
    logger.warning("Deep research dependencies not available. Install with 'pip install minion-agent[deep-research]'")

from typing import Any

import yaml
TIME_LIMIT_MULTIPLIER = 5
def load_config(config_path: str):
    with open(config_path, "r") as file:
        return yaml.safe_load(file)

class DeepResearcher:
    def __init__(
        self,
        budget: int = 6,
        remove_thinking_tags: bool = False,
        max_queries: int = -1,
        max_sources: int = -1,
        max_completion_tokens: int = 4096,
        user_timeout: float = 30.0,
        interactive: bool = False,
        planning_model: str = "together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        summarization_model: str = "together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        json_model: str = "together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        answer_model: str = "together_ai/deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
        debug_file_path: str | None = None,
        cache_dir: str | None = None,
        use_cache: bool = False,
        observer: Callable | None = None,
    ):
        self.budget = budget
        self.current_spending = 0
        self.remove_thinking_tags = remove_thinking_tags
        self.max_queries = max_queries
        self.max_sources = max_sources
        self.max_completion_tokens = max_completion_tokens
        self.user_timeout = user_timeout
        self.interactive = interactive
        self.planning_model = planning_model
        self.summarization_model = summarization_model
        self.json_model = json_model
        self.answer_model = answer_model
        self.debug_file_path = debug_file_path
        self.communication = UserCommunication()
        self.use_cache = use_cache

        # this is a little hack to make the observer optional
        self.observer = observer if observer is not None else lambda *args, **kwargs: None

        if self.use_cache:
            self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".open_deep_research_cache"
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            # Create a locks directory for the file locks
            self.locks_dir = self.cache_dir / ".locks"
            self.locks_dir.mkdir(parents=True, exist_ok=True)

        with open(os.path.join(os.path.dirname(__file__), "deep_research_prompts.yaml"), "r") as f:
            self.prompts = yaml.safe_load(f)

    def __call__(self, topic: str) -> str:
        """
        Makes the DeepResearcher instance callable.
        Runs research on the given topic and returns the answer.

        Args:
            topic: The research topic or question

        Returns:
            The research answer as a string
        """
        loop = asyncio.new_event_loop()
        try:
            answer = loop.run_until_complete(self.research_topic(topic))

            pending = asyncio.all_tasks(loop)
            if pending:
                loop.run_until_complete(asyncio.wait(pending, timeout=10))

            return answer
        finally:
            loop.close()

    async def research_topic(self, topic: str) -> str:
        """Main method to conduct research on a topic"""

        self.observer(0, "Starting research")

        # Step 0: Clarify the research topic
        if self.interactive:
            self.observer(0.05, "Clarifying research topic")
            clarified_topic = await self.clarify_topic(topic)
            self.observer(0.1, "Research topic clarified")
        else:
            clarified_topic = topic

        logger.info(f"Topic: {clarified_topic}")

        # Step 1: Generate initial queries
        self.observer(0.15, "Generating research queries")
        queries = await self.generate_research_queries(clarified_topic)
        queries = [clarified_topic] + queries[: self.max_queries - 1]
        all_queries = queries.copy()
        logger.info(f"Initial queries: {queries}")
        self.observer(0.2, "Research queries generated")

        if len(queries) == 0:
            logger.error("No initial queries generated")
            return "No initial queries generated"

        # Step 2: Perform initial search
        self.observer(0.25, "Performing initial search")
        results = await self.search_all_queries(queries)
        logger.info(f"Initial search complete, found {len(results.results)} results")
        self.observer(0.3, "Initial search complete")

        # Step 3: Conduct iterative research within budget
        total_iterations = self.budget - self.current_spending
        for iteration in range(self.current_spending, self.budget):
            current_iteration = iteration - self.current_spending + 1
            progress = 0.3 + (0.4 * (current_iteration / total_iterations))
            self.observer(progress, f"Conducting research iteration {current_iteration}/{total_iterations}")

            # Evaluate if more research is needed
            additional_queries = await self.evaluate_research_completeness(clarified_topic, results, all_queries)

            # Filter out empty strings and check if any queries remain
            additional_queries = [q for q in additional_queries if q]
            if not additional_queries:
                logger.info("No need for additional research")
                self.observer(progress + 0.05, "Research complete - no additional queries needed")
                break

            # for debugging purposes we limit the number of queries
            additional_queries = additional_queries[: self.max_queries]
            logger.info(f"Additional queries: {additional_queries}")

            # Expand research with new queries
            self.observer(progress + 0.02, f"Searching {len(additional_queries)} additional queries")
            new_results = await self.search_all_queries(additional_queries)
            logger.info(f"Follow-up search complete, found {len(new_results.results)} results")
            self.observer(progress + 0.05, f"Found {len(new_results.results)} additional results")

            results = results + new_results
            all_queries.extend(additional_queries)

        # Step 4: Generate final answer with feedback loop
        self.observer(0.7, "Filtering and processing results")
        logger.info(f"Generating final answer for topic: {clarified_topic}")
        results = results.dedup()
        logger.info(f"Deduplication complete, kept {len(results.results)} results")
        filtered_results, sources = await self.filter_results(clarified_topic, results)
        logger.info(f"LLM Filtering complete, kept {len(filtered_results.results)} results")
        self.observer(0.8, f"Results filtered: kept {len(filtered_results.results)} sources")

        if self.debug_file_path:
            with open(self.debug_file_path, "w") as f:
                f.write(f"{results}\n\n\n\n{filtered_results}")
                logger.info(f"Debug file (web search results and sources) saved to {self.debug_file_path}")

        # Generate final answer
        self.observer(0.9, "Generating final research report")
        while True:
            answer = await self.generate_research_answer(clarified_topic, filtered_results, self.remove_thinking_tags)

            if not self.interactive or self.current_spending >= self.budget:
                self.observer(0.95, "Research complete")
                return answer

            logger.info(f"Answer: {answer}")
            user_feedback = await self.communication.get_input_with_timeout(
                "\nAre you satisfied with this answer? (yes/no) If no, please provide feedback: ",
                self.user_timeout * TIME_LIMIT_MULTIPLIER,
            )

            if user_feedback.lower() == "yes" or not user_feedback or user_feedback == "":
                return answer

            # Regenerate answer with user feedback
            clarified_topic = f"{clarified_topic}\n\nReport:{answer}\n\nAdditional Feedback: {user_feedback}"
            logger.info(f"Regenerating answer with feedback: {user_feedback}")
            self.current_spending += 1

    async def clarify_topic(self, topic: str) -> str:
        """
        Engage in a multi-turn conversation to clarify the research topic.
        Returns the clarified topic after user confirmation or timeout.

        Args:
            topic: The research topic to clarify
            timeout: Number of seconds to wait for user input (default: 10)
        """

        CLARIFICATION_PROMPT = self.prompts["clarification_prompt"]

        clarification = await asingle_shot_llm_call(
            model=self.planning_model, system_prompt=CLARIFICATION_PROMPT, message=f"Research Topic: {topic}"
        )

        logger.info(f"\nTopic Clarification: {clarification}")

        while self.current_spending < self.budget:
            user_input = await self.communication.get_input_with_timeout(
                "\nPlease provide additional details or type 'continue' to proceed with the research: ", self.user_timeout
            )

            if user_input.lower() == "continue" or not user_input or user_input == "":
                return (
                    topic if not hasattr(self, "_clarification_context") else f"{topic}\n\nContext: {self._clarification_context}"
                )

            # Store the clarification context
            if not hasattr(self, "_clarification_context"):
                self._clarification_context = user_input
            else:
                self._clarification_context += f"\n{user_input}"

            # Get follow-up clarification if needed
            clarification = await asingle_shot_llm_call(
                model=self.planning_model,
                system_prompt=CLARIFICATION_PROMPT,
                message=f"Research Topic: {topic}\nPrevious Context: {self._clarification_context}",
            )

            logger.info(f"\nFollow-up Clarification: {clarification}")
            self.current_spending += 1

        # helps typing
        return topic

    async def generate_research_queries(self, topic: str) -> list[str]:
        PLANNING_PROMPT = self.prompts["planning_prompt"]

        plan = await asingle_shot_llm_call(
            model=self.planning_model, system_prompt=PLANNING_PROMPT, message=f"Research Topic: {topic}"
        )

        logger.info(f"\n\nGenerated deep research plan for topic: {topic}\n\nPlan: {plan}\n\n")

        SEARCH_PROMPT = self.prompts["plan_parsing_prompt"]

        response_json = await asingle_shot_llm_call(
            model=self.json_model,
            system_prompt=SEARCH_PROMPT,
            message=f"Plan to be parsed: {plan}",
            #response_format={"type": "json_object", "schema": ResearchPlan.model_json_schema()},
            response_format={"type": "json_schema", "json_schema": {"name":"ResearchPlan", "schema":ResearchPlan.model_json_schema()}},
        )

        plan = json.loads(response_json)

        return plan["queries"]

    def _get_cache_path(self, query: str) -> Path:
        """Generate a cache file path for a given query using its hash"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return self.cache_dir / f"tavily_{query_hash}.pkl"

    def _get_lock_path(self, cache_path: Path) -> Path:
        """Generate a lock file path for a given cache file"""
        return self.locks_dir / f"{cache_path.name}.lock"

    @contextmanager
    def _cache_lock(self, query: str):
        """Context manager for thread-safe cache operations"""
        cache_path = self._get_cache_path(query)
        lock_path = self._get_lock_path(cache_path)
        lock = FileLock(str(lock_path))
        try:
            with lock:
                yield cache_path
        finally:
            # Clean up lock file if it's stale
            if lock_path.exists() and not lock.is_locked:
                try:
                    lock_path.unlink()
                except FileNotFoundError:
                    pass

    def _save_to_cache(self, query: str, results: DeepResearchResults):
        """Save search results to cache in a thread-safe manner"""
        if not self.use_cache:
            return

        with self._cache_lock(query) as cache_path:
            with open(cache_path, "wb") as f:
                pickle.dump(results, f)

    def _load_from_cache(self, query: str) -> DeepResearchResults | None:
        """Load search results from cache if they exist in a thread-safe manner"""
        if not self.use_cache:
            return None

        try:
            with self._cache_lock(query) as cache_path:
                if cache_path.exists():
                    with open(cache_path, "rb") as f:
                        return pickle.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cache for query '{query}': {e}")
        return None

    async def search_all_queries(self, queries: List[str]) -> DeepResearchResults:
        """Execute searches for all queries in parallel, using thread-safe cache"""
        tasks = []
        cached_results = []
        results_list = []

        for query in queries:
            # Try to load from cache first if caching is enabled
            cached_result = self._load_from_cache(query)
            if cached_result is not None:
                logger.info(f"Using cached results for query: {query}")
                cached_results.append(cached_result)
            else:
                # If not in cache, create search task
                tasks.append(self._search_and_cache(query))

        results_list.extend(cached_results)

        # Execute remaining searches in parallel
        if tasks:
            res_list = await asyncio.gather(*tasks)
            results_list.extend(res_list)

        # Combine all results
        combined_results = DeepResearchResults(results=[])
        for results in results_list:
            combined_results = combined_results + results

        return combined_results

    async def _search_and_cache(self, query: str) -> DeepResearchResults:
        """Perform a search and cache the results"""
        results = await self._search_engine_call(query)
        self._save_to_cache(query, results)
        return results

    async def _search_engine_call(self, query: str) -> DeepResearchResults:
        """Perform a single search"""

        if len(query) > 400:
            # NOTE: we are truncating the query to 400 characters to avoid Tavily Search issues
            query = query[:400]
            logger.info(f"Truncated query to 400 characters: {query}")

        response = await atavily_search_results(query)

        logger.info("Tavily Search Called.")

        RAW_CONTENT_SUMMARIZER_PROMPT = self.prompts["raw_content_summarizer_prompt"]

        # Create tasks for summarization
        summarization_tasks = []
        result_info = []
        for result in response.results:
            if result.raw_content is None:
                continue
            task = self._summarize_content_async(result.raw_content, query, RAW_CONTENT_SUMMARIZER_PROMPT)
            summarization_tasks.append(task)
            result_info.append(result)

        # Use return_exceptions=True to prevent exceptions from propagating
        summarized_contents = await asyncio.gather(*summarization_tasks, return_exceptions=True)
        # Filter out exceptions
        summarized_contents = [result for result in summarized_contents if not isinstance(result, Exception)]

        formatted_results = []
        for result, summarized_content in zip(result_info, summarized_contents):
            formatted_results.append(
                DeepResearchResult(
                    title=result.title,
                    link=result.link,
                    content=result.content,
                    raw_content=result.raw_content,
                    filtered_raw_content=summarized_content,
                )
            )
        return DeepResearchResults(results=formatted_results)

    async def _summarize_content_async(self, raw_content: str, query: str, prompt: str) -> str:
        """Summarize content asynchronously using the LLM"""
        logger.info("Summarizing content asynchronously using the LLM")

        result = await asingle_shot_llm_call(
            model=self.summarization_model,
            system_prompt=prompt,
            message=f"<Raw Content>{raw_content}</Raw Content>\n\n<Research Topic>{query}</Research Topic>",
        )

        return result

    async def evaluate_research_completeness(self, topic: str, results: DeepResearchResults, queries: List[str]) -> list[str]:
        """
        Evaluate if the current search results are sufficient or if more research is needed.
        Returns an empty list if research is complete, or a list of additional queries if more research is needed.
        """

        # Format the search results for the LLM
        formatted_results = str(results)
        EVALUATION_PROMPT = self.prompts["evaluation_prompt"]

        evaluation = await asingle_shot_llm_call(
            model=self.planning_model,
            system_prompt=EVALUATION_PROMPT,
            message=(
                f"<Research Topic>{topic}</Research Topic>\n\n"
                f"<Search Queries Used>{queries}</Search Queries Used>\n\n"
                f"<Current Search Results>{formatted_results}</Current Search Results>"
            ),
        )

        logger.info(f"Evaluation: {evaluation}")

        EVALUATION_PARSING_PROMPT = self.prompts["evaluation_parsing_prompt"]

        response_json = await asingle_shot_llm_call(
            model=self.json_model,
            system_prompt=EVALUATION_PARSING_PROMPT,
            message=f"Evaluation to be parsed: {evaluation}",

            #response_format={"type": "json_object", "schema": ResearchPlan.model_json_schema()},
            response_format={"type": "json_schema",
                             "json_schema": {"name": "ResearchPlan", "schema": ResearchPlan.model_json_schema()}},
        )

        evaluation = json.loads(response_json)
        return evaluation["queries"]

    async def filter_results(self, topic: str, results: DeepResearchResults) -> tuple[DeepResearchResults, SourceList]:
        """Filter the search results based on the research plan"""

        # Format the search results for the LLM, without the raw content
        formatted_results = str(results)

        FILTER_PROMPT = self.prompts["filter_prompt"]

        filter_response = await asingle_shot_llm_call(
            model=self.planning_model,
            system_prompt=FILTER_PROMPT,
            message=(
                f"<Research Topic>{topic}</Research Topic>\n\n"
                f"<Current Search Results>{formatted_results}</Current Search Results>"
            ),
            # NOTE: This is the max_token parameter for the LLM call on Together AI, may need to be changed for other providers
            max_completion_tokens=4096,
        )

        logger.info(f"Filter response: {filter_response}")

        FILTER_PARSING_PROMPT = self.prompts["filter_parsing_prompt"]

        response_json = await asingle_shot_llm_call(
            model=self.json_model,
            system_prompt=FILTER_PARSING_PROMPT,
            message=f"Filter response to be parsed: {filter_response}",

            #response_format={"type": "json_object", "schema": SourceList.model_json_schema()},
            response_format={"type": "json_schema", "json_schema": {"name":"SourceList", "schema":SourceList.model_json_schema()}},
        )

        sources = json.loads(response_json)["sources"]

        logger.info(f"Filtered sources: {sources}")

        if self.max_sources != -1:
            sources = sources[: self.max_sources]

        # Filter the results based on the source list
        filtered_results = [results.results[i - 1] for i in sources if i - 1 < len(results.results)]

        return DeepResearchResults(results=filtered_results), sources

    async def generate_research_answer(self, topic: str, results: DeepResearchResults, remove_thinking_tags: bool = False):
        """
        Generate a comprehensive answer to the research topic based on the search results.
        Returns a detailed response that synthesizes information from all search results.
        """

        formatted_results = str(results)
        ANSWER_PROMPT = self.prompts["answer_prompt"]

        answer = await asingle_shot_llm_call(
            model=self.answer_model,
            system_prompt=ANSWER_PROMPT,
            message=f"Research Topic: {topic}\n\nSearch Results:\n{formatted_results}",
            # NOTE: This is the max_token parameter for the LLM call on Together AI, may need to be changed for other providers
            max_completion_tokens=self.max_completion_tokens,
        )

        # this is just to avoid typing complaints
        if answer is None or not isinstance(answer, str):
            logger.error("No answer generated")
            return "No answer generated"

        if remove_thinking_tags:
            # Remove content within <think> tags
            answer = self._remove_thinking_tags(answer)

        # Remove markdown code block markers if they exist at the beginning
        if answer.lstrip().startswith("```"):
            # Find the first line break after the opening backticks
            first_linebreak = answer.find("\n", answer.find("```"))
            if first_linebreak != -1:
                # Remove everything up to and including the first line break
                answer = answer[first_linebreak + 1 :]

            # Remove closing code block if it exists
            if answer.rstrip().endswith("```"):
                answer = answer.rstrip()[:-3].rstrip()

        return answer.strip()

    def _remove_thinking_tags(self, answer: str) -> str:
        """Remove content within <think> tags"""
        while "<think>" in answer and "</think>" in answer:
            start = answer.find("<think>")
            end = answer.find("</think>") + len("</think>")
            answer = answer[:start] + answer[end:]
        return answer

def create_agent(config: dict, return_instance: bool = False) -> Any:
    """Create a deep research agent from a config dict."""
    if not deep_research_available:
        raise ImportError("Deep research dependencies not available. Install with 'pip install minion-agent-x[deep-research]'")

    # Load config from file if path is provided
    if isinstance(config, str):
        config = load_config(config)

    # Get the agent type
    agent_type = config.get("type", "deep_research")

    # Get the agent config
    budget = config.get("budget", 6)
    remove_thinking_tags = config.get("remove_thinking_tags", False)
    max_queries = config.get("max_queries", -1)
    max_sources = config.get("max_sources", -1)
    max_completion_tokens = config.get("max_completion_tokens", 4096)
    user_timeout = config.get("user_timeout", 30.0)
    interactive = config.get("interactive", False)
    planning_model = config.get("planning_model", "together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo")
    summarization_model = config.get("summarization_model", "together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo")
    json_model = config.get("json_model", "together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo")
    answer_model = config.get("answer_model", "together_ai/deepseek-ai/DeepSeek-R1-Distill-Llama-70B")
    debug_file_path = config.get("debug_file_path", None)
    cache_dir = config.get("cache_dir", None)
    use_cache = config.get("use_cache", False)

    # Create the agent instance
    agent = DeepResearcher(
        budget=budget,
        remove_thinking_tags=remove_thinking_tags,
        max_queries=max_queries,
        max_sources=max_sources,
        max_completion_tokens=max_completion_tokens,
        user_timeout=user_timeout,
        interactive=interactive,
        planning_model=planning_model,
        summarization_model=summarization_model,
        json_model=json_model,
        answer_model=answer_model,
        debug_file_path=debug_file_path,
        cache_dir=cache_dir,
        use_cache=use_cache,
    )

    if return_instance:
        return agent

    def research_wrapper(goal: str):
        """Wrapper function to run research."""
        try:
            return agent(goal)
        except Exception as e:
            logger.error(f"Error in research: {e}")
            return str(e)

    def langchain_wrapper(goal: str):
        """Wrapper function to run research with langchain."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def run_graph():
                try:
                    return await agent.research_topic(goal)
                except Exception as e:
                    logger.error(f"Error in research: {e}")
                    return str(e)

            try:
                return loop.run_until_complete(run_graph())
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in research: {e}")
            return str(e)

    def base_llm_wrapper(goal: str):
        """Wrapper function to run research with base llm."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def get_answer():
                try:
                    return await asingle_shot_llm_call(
                        model=agent.answer_model,
                        system_prompt=agent.prompts["answer_prompt"],
                        message=goal,
                    )
                except Exception as e:
                    logger.error(f"Error in research: {e}")
                    return str(e)

            try:
                return loop.run_until_complete(get_answer())
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in research: {e}")
            return str(e)

    def smolagents_wrapper(goal: str):
        """Wrapper function to run research with smolagents."""
        try:
            return agent(goal)
        except Exception as e:
            logger.error(f"Error in research: {e}")
            return str(e)

    # Return the appropriate wrapper based on agent type
    if agent_type == "deep_research":
        return research_wrapper
    elif agent_type == "langchain":
        return langchain_wrapper
    elif agent_type == "base_llm":
        return base_llm_wrapper
    elif agent_type == "smolagents":
        return smolagents_wrapper
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")

class DeepResearchAgent(MinionAgent):
    name="deep_research"
    description="Deep Research Agent"
    
    def __init__(
        self, config: AgentConfig, managed_agents: Optional[list[AgentConfig]] = None
    ):
        super().__init__(config, managed_agents)
        logger.info("Initializing DeepResearchAgent")
        if not deep_research_available:
            logger.error("Deep research dependencies not available")
            raise ImportError(
                "You need to `pip install 'minion-agent[deep-research]'` to use this agent"
            )
        self.managed_agents = managed_agents
        self.config = config
        self._agent = None
        self._agent_loaded = False
        self._mcp_servers = None
        self._managed_mcp_servers = None
        logger.debug("DeepResearchAgent initialized with config: %s", config)

    @property
    def framework(self) -> AgentFramework:
        return AgentFramework.DEEP_RESEARCH

    def _get_model(self, agent_config: AgentConfig):
        """Get the model configuration for a smolagents agent."""
        # model_type = getattr(smolagents, agent_config.model_type or DEFAULT_MODEL_CLASS)
        # kwargs = {
        #     "model_id": agent_config.model_id,
        # }
        # model_args = agent_config.model_args or {}
        # if api_key_var := model_args.pop("api_key_var", None):
        #     kwargs["api_key"] = os.environ[api_key_var]
        # return model_type(**kwargs, **model_args)
        return None

    def _merge_mcp_tools(self, mcp_servers):
        """Merge MCP tools from different servers."""
        logger.debug("Merging MCP tools from %d servers", len(mcp_servers))
        tools = []
        for mcp_server in mcp_servers:
            tools.extend(mcp_server.tools)
        return tools

    async def _load_agent(self) -> None:
        """Load the agent instance."""
        logger.info("Loading agent")

        if not self.managed_agents and not self.config.tools:
            logger.debug("No managed agents or tools configured, using default tools")
            from minion_agent.tools.web_browsing import search_web,visit_webpage
            self.config.tools = [
                search_web,
                visit_webpage,
            ]

        try:
            tools, mcp_clients = await self._load_tools(
                self.config.tools or []
            )
            logger.info("Successfully imported and wrapped tools")
            self._mcp_servers = mcp_clients
            tools.extend(self._merge_mcp_tools(mcp_clients))

            managed_agents_instanced = []
            if self.managed_agents:
                logger.info("Loading managed agents")
                for managed_agent in self.managed_agents:
                    try:
                        if isinstance(managed_agent, MinionAgent):
                            managed_agents_instanced.append(managed_agent)
                            continue
                        if managed_agent.framework:
                            agent = await MinionAgent.create(managed_agent.framework, managed_agent)
                            managed_agents_instanced.append(agent)
                            logger.debug("Created managed agent with framework: %s", managed_agent.framework)
                            continue
                        
                        agent_type = getattr(
                            smolagents, managed_agent.agent_type or DEFAULT_AGENT_TYPE
                        )
                        managed_tools, managed_mcp_servers = await import_and_wrap_tools(
                            managed_agent.tools, agent_framework=AgentFramework.SMOLAGENTS
                        )
                        self._managed_mcp_servers = managed_mcp_servers
                        tools.extend(self._merge_mcp_tools(managed_mcp_servers))
                        
                        managed_agent_instance = agent_type(
                            name=managed_agent.name,
                            model=self._get_model(managed_agent),
                            tools=managed_tools,
                            verbosity_level=2,  # OFF
                            description=managed_agent.description
                            or f"Use the agent: {managed_agent.name}",
                        )
                        if managed_agent.instructions:
                            managed_agent_instance.prompt_templates["system_prompt"] = (
                                managed_agent.instructions
                            )
                        managed_agents_instanced.append(managed_agent_instance)
                        logger.debug("Created managed agent: %s", managed_agent.name)
                    except Exception as e:
                        logger.error("Failed to load managed agent: %s", str(e), exc_info=True)
                        raise

            # Set default configuration if config.agent_args is empty
            if not self.config.agent_args:
                self.config.agent_args = {
                    "type": "deep_researcher",
                    "max_steps": 2,
                    "max_queries": 5,
                    "max_sources": 40,
                    "max_completion_tokens": 8192,
                    "user_timeout": 30.0,
                    "interactive": True,
                    "use_cache": True,
                    "remove_thinking_tags": True,
                    "debug_file_path": "",
                    "planning_model": "together_ai/Qwen/Qwen2.5-72B-Instruct-Turbo",
                    "summarization_model": "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo",
                    "json_model": "together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
                    "answer_model": "together_ai/deepseek-ai/DeepSeek-V3"
                }
                logger.info("Using default deep research configuration")

            self._agent = create_agent(
                config=self.config.agent_args or {},
                return_instance=True
            )
            logger.info("Agent loaded successfully")
            
        except Exception as e:
            logger.error("Failed to load agent: %s", str(e), exc_info=True)
            raise

    async def _run_async(self, prompt: str,**kwargs: Any) -> Any:
        """Run the Smolagents agent with the given prompt."""
        logger.info("Running async research with prompt: %s", prompt)
        try:
            result = await self._agent.research_topic(prompt)
            logger.info("Research completed successfully")
            return result
        except Exception as e:
            logger.error("Research failed: %s", str(e), exc_info=True)
            raise

    @property
    def tools(self) -> List[str]:
        """
        Return the tools used by the agent.
        This property is read-only and cannot be modified.
        """
        return self._agent.tools
