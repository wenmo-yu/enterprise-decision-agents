"""外部情报专家配置。"""

from app.agent.prompts import sub_agents_content
from app.tools.tavily_tool import internet_search

network_search_agent = {
    "name": sub_agents_content["external_intelligence"]["name"],
    "description": sub_agents_content["external_intelligence"]["description"],
    "system_prompt": sub_agents_content["external_intelligence"]["system_prompt"],
    "tools": [internet_search],
}
