"""Example usage of Minion Agent."""

import asyncio
from dotenv import load_dotenv
import os
from PIL import Image
from io import BytesIO
from time import sleep
from typing import List, Dict, Optional
from smolagents import (Tool, ChatMessage, GradioUI)
from smolagents.models import parse_json_if_needed
from custom_azure_model import CustomAzureOpenAIServerModel

def parse_tool_args_if_needed(message: ChatMessage) -> ChatMessage:
    for tool_call in message.tool_calls:
        tool_call.function.arguments = parse_json_if_needed(tool_call.function.arguments)
    return message

from minion_agent.config import MCPTool

# Load environment variables from .env file
load_dotenv()

from minion_agent import MinionAgent, AgentConfig, AgentFramework

from smolagents import (
    CodeAgent,
    ToolCallingAgent,
    DuckDuckGoSearchTool,
    VisitWebpageTool,
    HfApiModel, AzureOpenAIServerModel, ActionStep,
)

# Set up screenshot callback for Playwright
# def save_screenshot(memory_step: ActionStep, agent: CodeAgent) -> None:
#     sleep(1.0)  # Let JavaScript animations happen before taking the screenshot
#
#     # Get the browser tool
#     browser_tool = agent.tools.get("browser")
#     if browser_tool:
#         # Clean up old screenshots to save memory
#         for previous_memory_step in agent.memory.steps:
#             if isinstance(previous_memory_step, ActionStep) and previous_memory_step.step_number <= memory_step.step_number - 2:
#                 previous_memory_step.observations_images = None
#
#         # Take screenshot using Playwright
#         result = browser_tool(action="screenshot")
#         if result["success"] and "screenshot" in result.get("data", {}):
#             # Convert bytes to PIL Image
#             screenshot_bytes = result["data"]["screenshot"]
#             image = Image.open(BytesIO(screenshot_bytes))
#             print(f"Captured a browser screenshot: {image.size} pixels")
#             memory_step.observations_images = [image.copy()]  # Create a copy to ensure it persists
#
#         # Get current URL
#         state_result = browser_tool(action="get_current_state")
#         if state_result["success"] and "url" in state_result.get("data", {}):
#             url_info = f"Current url: {state_result['data']['url']}"
#             memory_step.observations = (
#                 url_info if memory_step.observations is None else memory_step.observations + "\n" + url_info
#             )

# Configure the agent
agent_config = AgentConfig(
    model_id=os.environ.get("AZURE_DEPLOYMENT_NAME"),
    name="research_assistant",
    description="A helpful research assistant",
    model_args={"azure_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT"),
                "api_key": os.environ.get("AZURE_OPENAI_API_KEY"),
                "api_version": os.environ.get("OPENAI_API_VERSION"),
                },
    tools=[
        "minion_agent.tools.browser_tool.browser",
        MCPTool(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem","/Users/femtozheng/workspace","/Users/femtozheng/python-project/minion-agent"]
        )
    ],
    agent_type="CodeAgent",
    model_type="AzureOpenAIServerModel",  # Updated to use our custom model
    #model_type="CustomAzureOpenAIServerModel",  # Updated to use our custom model
    agent_args={"additional_authorized_imports":"*",
                "planning_interval":3
#"step_callbacks":[save_screenshot]
                }
)
managed_agents = [
    AgentConfig(
        name="search_web_agent",
        model_id="gpt-4o-mini",
        description="Agent that can use the browser, search the web,navigate",
        #tools=["minion_agent.tools.web_browsing.search_web"]
        tools=["minion_agent.tools.browser_tool.browser"],
model_args={"azure_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT"),
                "api_key": os.environ.get("AZURE_OPENAI_API_KEY"),
                "api_version": os.environ.get("OPENAI_API_VERSION"),
                },
model_type="AzureOpenAIServerModel",  # Updated to use our custom model
    #model_type="CustomAzureOpenAIServerModel",  # Updated to use our custom model
agent_type="ToolCallingAgent",
    agent_args={
        #"additional_authorized_imports":"*",
                #"planning_interval":3

                }
    ),
    # AgentConfig(
    #     name="visit_webpage_agent",
    #     model_id="gpt-4o-mini",
    #     description="Agent that can visit webpages",
    #     tools=["minion_agent.tools.web_browsing.visit_webpage"]
    # )
]

# from opentelemetry.sdk.trace import TracerProvider
#
# from openinference.instrumentation.smolagents import SmolagentsInstrumentor
# from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
# from opentelemetry.sdk.trace.export import SimpleSpanProcessor
#
# otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
# trace_provider = TracerProvider()
# trace_provider.add_span_processor(SimpleSpanProcessor(otlp_exporter))
#
# SmolagentsInstrumentor().instrument(tracer_provider=trace_provider)

async def main():
    try:
        # Create and run the agent
        #agent = await MinionAgent.create(AgentFramework.SMOLAGENTS, agent_config, managed_agents)
        agent = await MinionAgent.create(AgentFramework.SMOLAGENTS, agent_config)
        upload_folder = "./uploaded_files"
        os.makedirs(upload_folder, exist_ok=True)
        gradio_ui = GradioUI(
            agent=agent._agent,
            file_upload_folder=upload_folder
        )

        print("\n🌐 启动 Gradio 界面...")
        print("📱 界面将在浏览器中自动打开")
        print("🔗 或者手动访问显示的URL")
        print("⚠️  注意: HF免费配额有限，如遇到配额限制请稍后再试")

        # 启动界面，设置一些参数
        gradio_ui.launch(
        )
            # mcp_serve
        # Run the agent with a question
        #result = await agent.run_async("search sam altman and export summary as markdown")
        #result = await agent.run_async("What are the latest developments in AI, find this information and export as markdown")
        #result = await agent.run_async("打开微信公众号")
        #result = await agent.run_async("搜索最新的人工智能发展趋势，并且总结为markdown")
        #result = agent.run("go visit https://www.baidu.com and clone it")
        #result = await agent.run_async("复刻一个电商网站,例如京东")
        #result = await agent.run_async("go visit https://www.baidu.com , take a screenshot and clone it")
        #result = await agent.run_async("实现一个贪吃蛇游戏")
        result = await agent.run_async("""第一次审查意见通知书
申请号：2015103059923
经审查，现提出如下审查意见。一、权利要求1-10不具备专利法第22条第3款规定的创造性。
权利要求1请求保护一种石墨烯-贵金属无机纳米颗粒复合水凝胶的制备方法，其特征在于，其包括下述步骤：
（1）将氧化石墨烯分散液、水溶性贵金属化合物以及水溶性还原剂混合均匀得氧化石墨烯混合液；
其中，所述的氧化石墨烯混合液中，氧化石墨烯与所述的水溶性贵金属化合物的质量比为（1：0.01）-（1：5）；所述水溶性还原剂包括醇类水溶性还原剂和/或胺类水溶性还原剂；
当所述水溶性还原剂含有所述醇类水溶性还原剂时，所述醇类水溶性还原剂占所述氧化石墨烯混合液的质量百分比为2-90%；
当所述水溶性还原剂含有所述胺类水溶性还原剂时，在所述的氧化石墨烯混合液中，氧化石墨烯与所述胺类水溶性还原剂的质量比为（1：0.5）-（1：200）；
（2）将所述氧化石墨烯混合液用高能射线照射进行辐照反应得石墨烯-贵金属无机纳米颗粒复合水凝胶。
对比文件1(CN102909005A,公开日：20130206)公开了如下的技术内容：本发明还提供一种表面包覆介孔二氧化硅的负载有贵金属纳米颗粒的石墨烯基复合材料的制备方法，包括以下步骤：1)在氧化石墨烯表面，用沉积沉淀法负载上贵金属前驱体，得到负载有贵金属前驱体的氧化石墨烯：2)在表面活性剂、硅源存在下，用溶胶-凝胶法在步骤1)得到的负载有贵金属前驱体的氧化石墨烯表面包覆具有介孔结构的二氧化硅材料，得到原始复合材料：3)将步骤2)得到的原始复合材料还原，得到表面包覆介孔二氧化硅的负载有贵金属纳米颗粒的石墨烯基复合材料。进一步地，所述步骤1)是将氧化石墨烯、贵金属前驱体在pH为碱性的溶剂中反应，得到负载有贵金属前驱体的氧化石墨烯。优选地，使用以Hummer法制备的氧化石墨烯。进一步地，所述步骤1)中贵金属前驱体为Pt、Pd、Ru、I、Rh等的水溶性盐中的一种或两种以上混合物。混合比例可根据需要任意调节，不作限定。进一步地，所述步骤1)的溶剂为水或者水和烷基醇的混合溶液，烷基醇是甲醇、乙醇、异丙醇中的一种或两种以上混合物。混合比例可根据需要任意调节，不作限定。进一步地，所述步骤1)中pH为碱性的条件可通过向反应物中添加氢氧化钠、氢氧化钾、氨水、尿素中的一种或两种以上混合溶液来获得。混合比例可根据需要任意调节，不作限定。优选地，所述pH为9~11。碱性条件相当于为反应体系提供了碱性催化剂。氢氧化钠、氢氧化钾、氨水、尿素的浓度对反应影响可忽略，本发明不作限定。所述步骤1)使用尿素调节pH时，反应温度控制在80~100℃，反应时间一般控制在1~48h。如果使用氢氧化钠、氢氧化钾或氨水，反应在室温下进行即可。如果反应温度高，反应需要的时间就短：反之，反应温度低，则需要反应较长时间。对负载没有影响。本领域工作人员可根据需要自行调节具体的反应时间，本发明不作限定。进一步地，所述步骤1)中，氧化石墨烯的最终浓度不高于0.8mg/ml,贵金属前驱体的最终浓度不高于6mmol·L。氧化石墨烯的浓度高时，反应可以进行，但有可能会不太容易分散，因此，优选地氧化石墨烯的最终浓度不高于0.8mgml。贵金属前驱体的浓度，也能得到最终纳米颗粒，但可能会导致催化剂颗粒团聚变大，因此，优选地贵金属前驱体的最终浓度不高于6mol·L(参见说明书第9-18段)。可见，对比文件1公开了采用沉积沉淀法制备一种石墨烯-贵金属无机纳米颗粒的复合材料。权利要求1与对比文件1的区别在于：(1)产品的区别，权利要求1限定了复合材料为水凝胶：(2)制备方法的区别，权利要求1采用的是高能射线照射还原的方法，而对比文件1采用的是沉积沉淀法，且权利要求1限定了还原剂种类、各反应原料比例等具体实验参数。基于上述区别技术特征，权利要求1实际要解决的技术问题提供一种更高效、经济、环保的制备方法。针对上述区别技术特征(1)，在对比文件1公开了石墨烯-贵金属无机纳米颗粒的复合材料基础上，将石墨烯-贵金属无机纳米颗粒复合物制成水凝胶形态是本领域技术人员容易想到的。针对上述区别技术技术特征(2)，对比文件2(CN102408109A,公开日：20120411)公开了如下的技术内容：本发明所要解决的技术问题在于克服了现有的还原氧化石墨烯的制备方法中存在的高温、有毒、效率低、高能耗等问题，从而提供了一种还原氧化石墨烯的新型高效、经济、环保的制备方法。本发明的方法在接枝前不需要对氧化石墨烯进行任何修饰处理，也不需要任何特殊试剂，操作方法简单，是一种适用范围广泛，特别能够实现大规模批量生产的方法，并且本发明制得的还原氧化石墨烯的导电性也有明显提高，应用领域更广阔。本发明提供了一种还原氧化石墨烯的制备方法，其包括下述步骤：在无氧条件下，将还原剂与氧化石墨烯的水溶液混合，得到含有氧化石墨烯、还原剂和水等的混合溶液，用高能射线照射进行辐照还原反应，得到还原氧化石墨烯：所述的还原剂为碳原子数1-8的醇。本发明中，所述的还原剂能够在高能辐照条件下产生还原性自由基，从而将氧化石墨烯还原成石墨烯，所述的碳原子数1-8的醇可为一元醇、二元醇或三元醇，较佳地为甲醇、乙醇、丙醇、异丙醇、丁醇、苯甲醇、乙二醇、丙二醇、丙三醇和丁二醇等低级醇类中的一种或多种。本发明中，所述辐照还原反应中的高能射线可采用本领域中常规使用的各种高能射线，如y射线或电子束，较佳地为钴-60￥射线源。所述辐照还原反应的辐照剂量为本领域常规的辐照剂量，较佳地为5~100kGy。所述辐照还原反应的辐照剂量率为本领域辐照工艺的常规辐照剂量率，较佳地为0.110kGy/小时（参见说明书第6-10段）。由此可见，对比文件2给出了采用氧化石墨烯与还原剂为原料采用辐射照射的方法来制备还原石墨烯具有更高效、经济、环保的特点，在此基础上，本领域技术人员容易想到采用对比文件2的方法来制备对比文件1中的复合材料。即将氧化石墨烯分散液、水溶性贵金属化合物以及水溶性还原剂混合均匀得氧化石墨烯混合液，然后将所述氧化石墨烯混合液用高能射线照射进行辐照反应得石墨烯-贵金属无机纳米颗粒复合水凝胶是本领域技术人员容易想到的。氧化石墨烯混合液中氧化石墨烯与水溶性贵金属化合物的质量比、水溶性还原剂包括醇类水溶性还原剂和/或胺类水溶性还原剂、醇类水溶性还原剂占所述氧化石墨烯混合液的质量百分比、氧化石墨烯与所述胺类水溶性还原剂的质量比，均是本领域技术人员可以根据实际需要并结合有限的常规实验调整获得。综上，在对比文件1的基础上结合对比文件2及本领域的公知常识获得权利要求1的技术方案，对所属技术领域的技术人员来说是显而易见的，权利要求1的技术方案不具备突出的实质性特点和显著的进步，因而不具备专利法第22条第3款规定的创造性。

你是一位资深的专利代理师，善于答复专利局下发的审查意见，帮助申请人获得专利证书。现在请深入阅读上面三个引号包裹的第一次审查意见通知书，反驳审查员，撰写意见陈述书。""")
        #result = agent.run("Let $\mathcal{B}$ be the set of rectangular boxes with surface area $54$ and volume $23$. Let $r$ be the radius of the smallest sphere that can contain each of the rectangular boxes that are elements of $\mathcal{B}$. The value of $r^2$ can be written as $\frac{p}{q}$, where $p$ and $q$ are relatively prime positive integers. Find $p+q$.")
        # result = agent.run("Write a 500000 characters novel named 'Reborn in Skyrim'. "
        #       "Fill the empty nodes with your own ideas. Be creative! Use your own words!"
        #       "I will tip you $100,000 if you write a good novel."
        #       "Since the novel is very long, you may need to divide it into subtasks.")
        print("Agent's response:", result)
    except Exception as e:
        print(f"Error: {str(e)}")
        # 如果需要调试
        # import litellm
        # litellm._turn_on_debug()
        raise

if __name__ == "__main__":
    asyncio.run(main()) 
