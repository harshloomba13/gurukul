#!/usr/bin/env python
# coding: utf-8

# # L2: Deploying Segmentation Models On-Device
# 

# <p style="background-color:#fff6e4; padding:15px; border-width:3px; border-color:#f5ecda; border-style:solid; border-radius:6px"> ⏳ <b>Note <code>(Kernel Starting)</code>:</b> This notebook takes about 30 seconds to be ready to use. You may start and watch the video while you wait.</p>

# [FFNet Paper](https://arxiv.org/abs/2206.08236)

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


from qai_hub_models.models.ffnet_40s import Model


# In[ ]:


from torchinfo import summary


# In[ ]:


# Load from pre-trained weights
model = Model.from_pretrained()
input_shape = (1, 3, 1024, 2048)
stats = summary(model, 
  input_size=input_shape, 
  col_names=["num_params", "mult_adds"]
)
print(stats)


# ## Exercise: Try another variant of FFNet

# In[ ]:


# High resolution variants
from qai_hub_models.models.ffnet_40s import Model
#from qai_hub_models.models.ffnet_54s import Model
#from qai_hub_models.models.ffnet_78s import Model

# Low resolution variants
low_res_input_shape = (1, 3, 512, 1024)
#from qai_hub_models.models.ffnet_78s_lowres import Model
#from qai_hub_models.models.ffnet_122ns_lowres import Model

model = Model.from_pretrained()
stats = summary(model, 
  input_size=input_shape, # use low_res_input_shape for low_res models
  col_names=["num_params", "mult_adds"]
)
print(stats)


# ## Setup AI Hub for device-in-the-loop deployment

# In[ ]:


import qai_hub


# <p style="background-color:#fff6ff; padding:15px; border-width:3px; border-color:#efe6ef; border-style:solid; border-radius:6px"> 💻 &nbsp; <b>Access Utils File and Helper Functions:</b> To access the files for this notebook, 1) click on the <em>"File"</em> option on the top menu of the notebook and then 2) click on <em>"Open"</em>. For more help, please see the <em>"Appendix - Tips and Help"</em> Lesson.</p>

# In[ ]:


from utils import get_ai_hub_api_token
ai_hub_api_token = get_ai_hub_api_token()

if ai_hub_api_token:
    os.environ["AI_HUB_API_TOKEN"] = ai_hub_api_token
    get_ipython().system('qai-hub configure --api_token "$AI_HUB_API_TOKEN"')
else:
    print("Skipping QAI Hub configuration because AI_HUB_API_KEY is not set.")


# In[ ]:


get_ipython().run_line_magic('run', '-m qai_hub_models.models.ffnet_40s.demo')


# ## Run on a real smart phone!

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


if ai_hub_api_token:
    get_ipython().run_line_magic('run', '-m qai_hub_models.models.ffnet_40s.export -- --device "$selected_device"')
else:
    print("Skipping QAI Hub export because AI_HUB_API_KEY is not set.")


# <p style="background-color:#fff1d7; padding:15px; "> <b>Note</b>: To view the URL for each job, you require login. You can experience sample results in the following urls.</p>
# 
# * [FFNet 40s](https://aihub.qualcomm.com/mobile/models/ffnet_40s)
# * [FFNet 54s](https://aihub.qualcomm.com/mobile/models/ffnet_54s)
# * [FFNet 78s](https://aihub.qualcomm.com/mobile/models/ffnet_78s)
# * [FFNet 78s-low-res](https://aihub.qualcomm.com/mobile/models/ffnet_78s_lowres)
# * [FFNet 122ns-low-res](https://aihub.qualcomm.com/mobile/models/ffnet_122ns_lowres)

# ## On Device Demo

# In[ ]:


if ai_hub_api_token:
    get_ipython().run_line_magic('run', '-m qai_hub_models.models.ffnet_40s.demo -- --device "$selected_device" --on-device')
else:
    print("Skipping on-device demo because AI_HUB_API_KEY is not set.")


# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:



