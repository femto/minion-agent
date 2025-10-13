import asyncio
import os

import litellm
from dotenv import load_dotenv
from minion_agent.config import AgentConfig, AgentFramework, MCPStdio
from minion_agent import MinionAgent
from smolagents import AzureOpenAIServerModel, CodeAgent
import minion_agent

# Load environment variables
load_dotenv()

async def main():


    # Configure the main agent that will drive the research
    main_agent_config = AgentConfig(
        model_id=os.environ.get("AZURE_DEPLOYMENT_NAME"),
        name="main_agent",
        description="Main agent that coordinates research and saves results",
        model_args={"azure_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT"),
                    "api_key": os.environ.get("AZURE_OPENAI_API_KEY"),
                    "api_version": os.environ.get("OPENAI_API_VERSION"),
                    },
        model_type=AzureOpenAIServerModel,  # Updated to use our custom model
        # model_type="CustomAzureOpenAIServerModel",  # Updated to use our custom model
        agent_type=CodeAgent,
        agent_args={"additional_authorized_imports": "*",
                    # "planning_interval":3
                    },
        tools=[
            MCPStdio(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", "/Users/femtozheng/workspace",
                      "/Users/femtozheng/python-project/minion-agent"]
            )
        ],
    )
    #litellm._turn_on_debug()
    # Configure the deep research agent
    research_agent_config = AgentConfig(
        framework=AgentFramework.DEEP_RESEARCH,
        model_id=os.environ.get("AZURE_DEPLOYMENT_NAME"),
        name="research_assistant",
        description="A helpful research assistant that conducts deep research on topics",
        agent_args={
            "planning_model": "azure/" + os.environ.get("AZURE_DEPLOYMENT_NAME"),
            "summarization_model": "azure/" + os.environ.get("AZURE_DEPLOYMENT_NAME"),
            "json_model": "azure/" + os.environ.get("AZURE_DEPLOYMENT_NAME"),
            "answer_model": "azure/" + os.environ.get("AZURE_DEPLOYMENT_NAME")
        }
    )

    # Create the main agent with the research agent as a managed agent
    main_agent = await MinionAgent.create_async(
        AgentFramework.SMOLAGENTS,
        main_agent_config,
        managed_agents=[research_agent_config]
    )

    # Example research query
    research_query = """
    Research The evolution of Indo-European languages, and generate a pdf out of it.
    """

    try:
        # Run the research through the main agent
        result = await main_agent.run_async(research_query)
        
        print("\n=== Research Results ===\n")
        print(result)
        
        # Save the results to a file
        # output_path = "research_results.md"
        # with open(output_path, "w") as f:
        #     f.write(result)
        #
        # print(f"\nResults saved to {output_path}")
        
    except Exception as e:
        print(f"Error during research: {str(e)}")

if __name__ == "__main__":
    # Set up environment variables if needed
    if not os.getenv("AZURE_OPENAI_API_KEY"):
        print("Please set AZURE_OPENAI_API_KEY environment variable")
        exit(1)
    
    asyncio.run(main())
