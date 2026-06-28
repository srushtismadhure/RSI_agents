import json
import time
import traceback

from methods.execution_agent import execute_playbook_and_get_response
from methods.ThinkRemed.probe_agent import get_probe_response
from methods.ThinkRemed.tools import print_playbook_function, probe_function
from methods.ThinkRemed.verification_agent import verify_status
from models.llm import chat_api

WAIT_REME_TIME = 10
MAX_RETRY_TIME = 1


def remediate_failure(client, runtime_envs, namespace, root_cause, failure_category):
    print("=" * 50)
    print(f"Start to remediate root cause: {root_cause}, failure category: {failure_category}")

    with open("inventory.ini", "r") as fr:
        inventory_content = fr.read()

    # 初始提示
    root_prompt = f'''You are an experienced SRE managing a microservice system.
    A failure has occurred, and your task is to generate a final executable Ansible playbook based on the given root cause, failure category, and the probed information (executed by "ansible-playbook -i inventory.ini remediation.yml").
    The system will automatically execute the playbook and verify whether the failure has been successfully resolved.  
    [Attention] Please ensure that online services remain uninterrupted; restarting services should not be considered a primary strategy.
    {runtime_envs}
    The content of inventory.ini is {inventory_content}
    The current namespace is: {namespace}, failure root cause service is: {root_cause}, and the failure category is: {failure_category}.'''

    prompts = [{"role": "system", "content": root_prompt}]

    def get_playbook_with_probing():
        """循环调用 LLM，支持 probe 查询，直到返回 playbook"""
        nonlocal prompts
        while True:
            response_message, tools = chat_api(prompts, tools=[print_playbook_function, probe_function])
            if not tools:
                return ""

            # 如果返回了 print_playbook，直接返回
            if tools and tools[0]["function"]["name"] == "print_playbook":
                try:
                    print(tools[0]["function"]["arguments"])
                    prompts.append({"role": "assistant", "content": tools[0]["function"]["arguments"]})
                    return json.loads(tools[0]["function"]["arguments"])["code"]
                except:
                    prompts.append({"role": "assistant", "content": "Error Code"})
                    return ""

            # 否则处理所有 probe 工具调用
            for tool in tools or []:
                print("think:" + str(tool))
                try:
                    # 执行探测命令
                    tool_result = get_probe_response(client, json.loads(tool["function"]["arguments"])["cmds"])
                    # 记录工具调用结果（作为 function role 的消息）
                    prompts.append({"role": "assistant", "content": tool_result})

                    # 继续追问
                    round_prompt = '''Please continue to generate executable Ansible playbook or get more information from the probe agent.'''
                    prompts.append({"role": "user", "content": round_prompt})
                except:
                    pass

            # 继续循环，不退出

    # 第一次尝试获取 playbook
    try:
        playbook_code = get_playbook_with_probing()
    except Exception as e:
        traceback.print_exc()
        print(f"Failed to generate playbook: {e}")
        return False, -1

    # 执行 playbook 并验证
    def execute_and_verify():
        status, output = execute_playbook_and_get_response(client, playbook_code)
        if status:
            time.sleep(WAIT_REME_TIME)
            verify_status_result = verify_status(
                namespace=namespace,
                label=f"app={root_cause}",
                type=failure_category
            )
            return status, verify_status_result, output
        return status, False, output

    # 第一次执行
    playbook_exec_status, status, output = execute_and_verify()

    # 记录执行结果
    prompts.append({"role": "assistant", "content": f"playbook execution response: {output}"})

    # 重试循环
    try_time = 1
    while not status and try_time <= MAX_RETRY_TIME:
        retry_prompt = f'''The failure of online service has not yet been remediated.
        You may use the probe agent to further inspect the system state and generate a new Ansible playbook to attempt remediation again.
        The previous playbook execution returned: {playbook_exec_status}, output: {status}'''
        prompts.append({"role": "user", "content": retry_prompt})

        try:
            playbook_code = get_playbook_with_probing()
        except Exception as e:
            print(f"Retry failed to generate playbook: {e}")
            break

        playbook_exec_status, status, output = execute_and_verify()
        try_time += 1

        # 记录执行结果
        prompts.append({"role": "assistant", "content": f"playbook execution response: {output}"})

    return prompts, try_time
