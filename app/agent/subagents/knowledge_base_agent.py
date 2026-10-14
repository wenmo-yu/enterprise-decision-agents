"""内部知识专家配置。"""

from app.agent.prompts import sub_agents_content
from app.tools.knowledge_tools import search_internal_knowledge

knowledge_base_agent = {
    "name": sub_agents_content["internal_knowledge"]["name"],
    "description": sub_agents_content["internal_knowledge"]["description"],
    "system_prompt": sub_agents_content["internal_knowledge"]["system_prompt"],
    "tools": [search_internal_knowledge],
}
