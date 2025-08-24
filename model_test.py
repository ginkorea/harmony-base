import os
os.environ["TRANSFORMERS_NO_MXFP4"] = "1"

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Prevent MXFP4 fallback
os.environ["TRANSFORMERS_NO_MXFP4"] = "1"

MODEL_PATH = "./models/gpt-oss-20b"

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    torch_dtype=torch.float16,  # less memory than bfloat16
    device_map="auto",
    low_cpu_mem_usage=True
)

input_ids = tokenizer("Hello, who are you?", return_tensors="pt").input_ids.to(model.device)
output = model.generate(input_ids, max_new_tokens=50)
print(tokenizer.decode(output[0], skip_special_tokens=True))
