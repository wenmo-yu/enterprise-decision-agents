"""经营分析专家：通过服务边界复用独立的语义问数项目。"""

from app.agent.prompts import sub_agents_content
from app.tools.analytics_query_tool import analytics_query

database_query_agent = {
    "name": sub_agents_content["analytics"]["name"],
    "description": sub_agents_content["analytics"]["description"],
    "system_prompt": sub_agents_content["analytics"]["system_prompt"],
    "tools": [analytics_query],
}
