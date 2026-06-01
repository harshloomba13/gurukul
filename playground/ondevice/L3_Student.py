#!/usr/bin/env python
# coding: utf-8

# # L3: Preparing for on-device deployment
# 

# <p style="background-color:#fff6e4; padding:15px; border-width:3px; border-color:#f5ecda; border-style:solid; border-radius:6px"> ⏳ <b>Note <code>(Kernel Starting)</code>:</b> This notebook takes about 30 seconds to be ready to use. You may start and watch the video while you wait.</p>
# 

# ## Capture trained model

# In[ ]:


import os
import shlex
import subprocess
import sys


try:
    get_ipython
except NameError:
    class _ScriptIPython:
        def system(self, command):
            command = os.path.expandvars(command)
            subprocess.run(command, shell=True, check=True)

        def run_line_magic(self, magic, argument):
            if magic != "run":
                raise NotImplementedError(f"Unsupported IPython magic: {magic}")

            for name, value in globals().items():
                argument = argument.replace(f"${name}", str(value))
                argument = argument.replace(f'"${name}"', str(value))

            args = shlex.split(argument)
            subprocess.run([sys.executable, *args], check=True)

    def get_ipython():
        return _ScriptIPython()


from qai_hub_models.models.ffnet_40s import Model as FFNet_40s

# Load from pre-trained weights
ffnet_40s = FFNet_40s.from_pretrained()


# In[ ]:


import torch
input_shape = (1, 3, 1024, 2048)
example_inputs = torch.rand(input_shape)


# In[ ]:


traced_model = torch.jit.trace(ffnet_40s, example_inputs)


# In[ ]:


traced_model


# ## Compile for device

# <p style="background-color:#fff6ff; padding:15px; border-width:3px; border-color:#efe6ef; border-style:solid; border-radius:6px"> 💻 &nbsp; <b>Access Utils File and Helper Functions:</b> To access the files for this notebook, 1) click on the <em>"File"</em> option on the top menu of the notebook and then 2) click on <em>"Open"</em>. For more help, please see the <em>"Appendix - Tips and Help"</em> Lesson.</p>

# In[ ]:


import qai_hub
import qai_hub_models

from utils import get_ai_hub_api_token
ai_hub_api_token = get_ai_hub_api_token()

if ai_hub_api_token:
    os.environ["AI_HUB_API_TOKEN"] = ai_hub_api_token
    get_ipython().system('qai-hub configure --api_token "$AI_HUB_API_TOKEN"')
else:
    print("Skipping QAI Hub configuration because AI_HUB_API_KEY is not set.")


# In[ ]:


if ai_hub_api_token:
    for device in qai_hub.get_devices():
        print(device.name)
else:
    print("Skipping QAI Hub device listing because AI_HUB_API_KEY is not set.")


# <p style="background-color:#fff6e4; padding:15px; border-width:3px; border-color:#f5ecda; border-style:solid; border-radius:6px"> ⏳ <b>Note:</b> To spread the load across various devices, we are selecting a random device. Feel free to change it to any other device you prefer.</p>

# In[ ]:


devices = [
    "Samsung Galaxy S22 Ultra 5G",
    "Samsung Galaxy S22 5G",
    "Samsung Galaxy S22+ 5G",
    "Samsung Galaxy Tab S8",
    "Xiaomi 12",
    "Xiaomi 12 Pro",
    "Samsung Galaxy S22 5G",
    "Samsung Galaxy S23",
    "Samsung Galaxy S23+",
    "Samsung Galaxy S23 Ultra",
    "Samsung Galaxy S24",
    "Samsung Galaxy S24 Ultra",
    "Samsung Galaxy S24+",
]

import random
selected_device = random.choice(devices)
print(selected_device)


# In[ ]:


device = qai_hub.Device(selected_device)

if ai_hub_api_token:
    # Compile for target device
    compile_job = qai_hub.submit_compile_job(
        model=traced_model,                        # Traced PyTorch model
        input_specs={"image": input_shape},        # Input specification
        device=device,                             # Device
    )
else:
    compile_job = None
    print("Skipping QAI Hub compile job because AI_HUB_API_KEY is not set.")


# In[ ]:


# Download and save the target model for use on-device
target_model = compile_job.get_target_model() if compile_job else None


# ## Exercise: Try different runtimes 

# In[ ]:


compile_options="--target_runtime tflite"                  # Uses TensorFlow Lite
compile_options="--target_runtime onnx"                    # Uses ONNX runtime
compile_options="--target_runtime qnn_lib_aarch64_android" # Runs with Qualcomm AI Engine

if ai_hub_api_token:
    compile_job_expt = qai_hub.submit_compile_job(
        model=traced_model,                        # Traced PyTorch model
        input_specs={"image": input_shape},        # Input specification
        device=device,                             # Device
        options=compile_options,
    )
else:
    compile_job_expt = None
    print("Skipping QAI Hub experimental compile job because AI_HUB_API_KEY is not set.")


# Expore more compiler options <a href=https://app.aihub.qualcomm.com/docs/hub/compile_examples.html#compiling-pytorch-to-tflite> here</a>.

# ## On-Device Performance Profiling

# In[ ]:


from qai_hub_models.utils.printing import print_profile_metrics_from_job

# Choose device
device = qai_hub.Device(selected_device)

if ai_hub_api_token and target_model:
    # Runs a performance profile on-device
    profile_job = qai_hub.submit_profile_job(
        model=target_model,                       # Compiled model
        device=device,                            # Device
    )

    # Print summary
    profile_data = profile_job.download_profile()
    print_profile_metrics_from_job(profile_job, profile_data)
else:
    profile_job = None
    print("Skipping QAI Hub profile job because AI_HUB_API_KEY is not set.")


# ## Exercise: Try different compute units

# In[ ]:


profile_options="--compute_unit cpu"     # Use cpu 
profile_options="--compute_unit gpu"     # Use gpu (with cpu fallback) 
profile_options="--compute_unit npu"     # Use npu (with cpu fallback) 

if ai_hub_api_token and target_model:
    # Runs a performance profile on-device
    profile_job_expt = qai_hub.submit_profile_job(
        model=target_model,                     # Compiled model
        device=device,                          # Device
        options=profile_options,
    )
else:
    profile_job_expt = None
    print("Skipping QAI Hub experimental profile job because AI_HUB_API_KEY is not set.")


# ## On-Device Inference

# In[ ]:


sample_inputs = ffnet_40s.sample_inputs()
sample_inputs


# In[ ]:


torch_inputs = torch.Tensor(sample_inputs['image'][0])
torch_outputs = ffnet_40s(torch_inputs)
torch_outputs


# In[ ]:


if ai_hub_api_token and target_model:
    inference_job = qai_hub.submit_inference_job(
            model=target_model,          # Compiled model
            inputs=sample_inputs,        # Sample input
            device=device,               # Device
    )
else:
    inference_job = None
    print("Skipping QAI Hub inference job because AI_HUB_API_KEY is not set.")


# In[ ]:


ondevice_outputs = inference_job.download_output_data() if inference_job else None
if ondevice_outputs:
    ondevice_outputs['output_0']


# In[ ]:


from qai_hub_models.utils.printing import print_inference_metrics
if inference_job and ondevice_outputs:
    print_inference_metrics(inference_job, ondevice_outputs, torch_outputs)
else:
    print("Skipping QAI Hub inference metrics because AI_HUB_API_KEY is not set.")


# ## Get ready for deployment!

# In[ ]:


if compile_job:
    target_model = compile_job.get_target_model()
    _ = target_model.download("FFNet_40s.tflite")
else:
    print("Skipping target model download because AI_HUB_API_KEY is not set.")


# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:



