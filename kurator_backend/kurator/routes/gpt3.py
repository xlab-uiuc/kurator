import anyio
import difflib
from string import Template

from fastapi import APIRouter
from pydantic import BaseModel

from kurator.utils import Model, CodexModel, SRC_PATH

router = APIRouter()

prompt_template = (SRC_PATH/"routes/prompt_template.txt").read_text()

# have to do this ugly thing because anyio.to_thread.run_sync doesn't pass keyword arguments to the function :facepalm:
CodexModelForInstructions = Model("openai", "code-davinci-002", stop="<<END>>")

class QueryGPT3Payload(BaseModel):
    before: str
    after: str

class QueryGPT3NewConfigPayload(BaseModel):
    before: str
    change_instruction: str


def get_prompt_for_gpt3(diff):
    # replace the diff
    prompt = Template(prompt_template).substitute(diff_goes_here=diff)
    return prompt

async def query_codex(model, prompt, **kwargs):
    return await anyio.to_thread.run_sync(model.query, prompt, **kwargs)

async def get_instructions_from_gpt3(before: str, after: str):
    diff = difflib.ndiff(before.splitlines(), after.splitlines())
    diff = '\n'.join(diff)

    prompt = get_prompt_for_gpt3(diff)
    choices = await query_codex(CodexModelForInstructions, prompt)

    processed_responses = []
    for choice in choices:
        if choice.endswith("No other changes have been made."):
            choice = choice[:-len("No other changes have been made.")].strip()
        if "In imperative form:" in choice:
            # print(choice)
            choice = choice.split("In imperative form:")[1].strip()
            if choice.startswith("```"):
                choice = choice[len("```"):]
            if choice.endswith("```"):
                choice = choice[:-len("```")].strip()

        processed_responses.append(choice)
    
    return processed_responses[0]


@router.post('/api/query_gpt3')
async def query_gpt3(payload: QueryGPT3Payload):
    return await get_instructions_from_gpt3(payload.before, payload.after)


@router.post('/api/query_gpt3_new_config')
async def generate_new_config(payload: QueryGPT3NewConfigPayload):
    # takes in a config and change instructions, and generates a new config
    before = payload.before
    instr = payload.change_instruction

    prompt  = "Consider the following Kubernetes configuration:\n\n"
    prompt += "```yaml\n" + before + "\n```\n\n"
    prompt += "Follow the given instructions and generate a new configuration:\n\n"
    prompt += "```\n" + instr + "\n```\n\n"
    prompt += "The new configuration is:\n\n"
    prompt += "```yaml\n"

    #choices = get_codex_solutions(prompt, stop=["```"], toks=[1500], num_solutions=1)
    choices = await query_codex(CodexModel, prompt)

    return choices[0]