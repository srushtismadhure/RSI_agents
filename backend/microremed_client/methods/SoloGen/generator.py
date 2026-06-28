import json
import os
import time
import traceback

from methods.SoloGen.tools import print_playbook_function
from methods.execution_agent import execute_playbook_and_get_response
from models.llm import chat_api

WAIT_REME_TIME = 10
MAX_RETRY_TIME = 3


def remediate_failure(client, runtime_envs, namespace, root_cause, failure_category):
    print("=" * 50)
    print(f"Start to remediate root cause: {root_cause}, failure category: {failure_category}")

    with open("inventory.ini", "r") as fr:
        inventory_content = fr.read()

    # 初始提示
    root_prompt = f'''You are an experienced SRE managing a microservice system.
    A failure has occurred, and your task is to generate a final executable Ansible playbook based on the given root cause and failure category (executed by "ansible-playbook -i inventory.ini remediation.yml").
    The system will automatically execute the playbook and verify whether the failure has been successfully resolved.  
    [Attention] Please ensure that online services remain uninterrupted; restarting services should not be considered a primary strategy.
    {runtime_envs}
    The content of inventory.ini is {inventory_content}
    The current namespace is: {namespace}, failure root cause service is: {root_cause}, and the failure category is: {failure_category}.'''

    prompts = [{"role": "system", "content": root_prompt}]
    _, tools = chat_api(prompts, tools=[print_playbook_function])
    playbook_code = ""
    if tools and tools[0]["function"]["name"] == "print_playbook":
        try:
            prompts.append({"role": "assistant", "content": tools[0]["function"]["arguments"]})
            print(tools[0]["function"]["arguments"])
            playbook_code = json.loads(tools[0]["function"]["arguments"])["code"]
        except:
            prompts.append({"role": "assistant", "content": "Error Code"})
            playbook_code = ""

    execute_playbook_and_get_response(client, playbook_code)
    time.sleep(WAIT_REME_TIME)
    return prompts, 1
