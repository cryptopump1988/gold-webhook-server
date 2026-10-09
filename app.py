from flask import Flask, request, Response
import requests
import os
import json
import base64
from datetime import datetime, timezone
from pywebpush import webpush, WebPushException

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TWELVE_DATA_KEY = os.environ.get("TWELVE_DATA_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # format: username/gold-webhook-server
HISTORY_PATH = "data/history.json"
SUBS_PATH = "data/subscriptions.json"
MAX_HISTORY = 100

# Accept the key as a one-line base64 string OR as a pasted PEM block (header/footer + line breaks);
# pywebpush only understands the one-line form, so a PEM paste fails with "ASN.1 parsing error".
_vapid_raw = os.environ.get("VAPID_PRIVATE_KEY", "").strip().replace("\\n", "\n")
if "BEGIN" in _vapid_raw:
    _vapid_raw = "".join(l.strip() for l in _vapid_raw.splitlines() if l.strip() and not l.strip().startswith("-----"))
VAPID_PRIVATE_KEY = _vapid_raw
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_CLAIMS_EMAIL = os.environ.get("VAPID_CLAIMS_EMAIL", "mailto:admin@bakalestrading.app")

TELEGRAM_SEND_MSG_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
TELEGRAM_SEND_PHOTO_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

ICON_192_B64 = "iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAMAAABlApw1AAAAYFBMVEWWdx/wyl+ykDHYoxJ0XiAMEBYfHhrYtFEMEBYKDxn6wyyymEuMekFGPigNERb5twACCBcAAADrrAJGOREtJxT91Wa4iAdXRRFwVhD+wgCGZg6oiC88MRLNlwRjTQ+adAykraapAAAAIHRSTlP//////5/t/10j//////7//wD//////////////////0aQzhUAAA6vSURBVHja1Z2LgqsoDECxVNvO7FquWrXWx///5RLAZwmC4t6W3fuazmgOJCFEDOTPWrtdwzCK4v+9RVEYXm+r4pE14f+C6DOMNQgTwDWMP6KF1y0Atw+RXjHcHAE+S3wTgh7g48QXCNYA1/hD29UK4BbGH9s0ekS+pvuRQSDfJf87AfkC6zXaMvk2+ZcEM4Ao/ooWYQBh/CUt1AN8jfwzAvKN8k8JyNf4T8SbDgBH3IWpdsS1lwDhoXIfQBLOAa4+ZY+ztKy6PG8S1Zo876oyzWKfFNcZgC/p47rs8uR+vz/viwZfSPKurGNfDFOA0IvwaSVkB0l5uyej9Al8pf97XqVeIMIR4LZf/LjoqJJ9Ijf8I5l/RfxBuyLej3AbAEJP0ivxEpqTqiyKNMsy+myzumiLc5c3NJlAeGAIe4DbPvGzqpFqAq0hYKyqZVmcPwv+h2x1wQ2kuQ/f3FTZPoSbAgj3iJ/mg0C0a7Neu6MoApkBoBe/ruGPtFCWIn7L0z0IoQLYLn5c5GN3Lv3LAkAgpGkKv5eE9gw516Q9johsnwMYKxolBe3qd4XWAQABNM4gxgF+NcXmUbgKgHCP8ggJWq05RguAegIArah6/s2KFAqAbfJnRN2dpIhTNwMU3Eul51y5V5KxjTpENmkQY2Uixe9wR6IDSKcjAAilQkjKTYNw5QAbNIjVzXNN/FWAQjaJkNyfTc226BC5Re7dX8leW1FdOwDeeluo3AchupGbu/bL7k/alftZAxRFJxWycbeEG3E1AVbIKbdad99vE9kUYCp/W4AeQfxXuBJcHQGE+kBf2Ti+d4A0xQiKim5SoytxsmEW5+I2ndXs6QDQqkHghuU2MYckclN/cZPWrpucADhCB8sGR0OIXABYljiZmhFgIX3blmVxboQhuBBExEH+1nGMDQAz4UvxPydoS0HAR9heKnsAVkrvY29l0RRAIz8Xedna3JWAOMpfOnQOFzuiOgBMfCAgysp8Ayj5W1c/3a/IprNAL/55bNsJiL3+8wtbhisy+wOrL75iqIqiTuUgjPJL8cnQqglDlbgQ2AGwWshv5R5kdqiCtNaYi2jyrirSGhhk98/EVwxzAktfRGz9J28W/S+Ez5O7ttG8amEEdOIDwYAgZntLb2oDwOLGalBFbqsZM0LTNmQZu5n4p9Ppxf87LQiEHTRW/toKIAf51/wPY1nZTFNbIifK5eiVKUkopSJTSs5K+tfY5qYgCHJPADL8r9ia+F0yZIco4coC85j0QmnaSqMABJrcKT0txFcIlRqEswyMKuYDgBXrvQHi931Pc5EdkjNZTMf1AGSERML6Dhgv8nrhBJUcTIvomtgY8Jo+srhSnZ+QYpIdmszEtZwIRFYL5P/5oS89gdCiM7giK7+3DtCs+bRxhd+U2SxDMQcQHpTb7wukF79er9PlMjeEDgg4QnXuRLpsNwCrnisTMMvyMcfGFsHQEkB6oBMXH1oQPHgLJgyCgCPAb7DYf66aAVmfwZJ7x1bmaGSN9g7Qe1BAENKLFlDwpZJAAFSiNTaTD7FQIIMBsLgT4uvTOjMAmMJaKT9IS0f5eeME0ivJIVAtsVAishLCPflFUmbMUEBiLUZyczMAoUES4HX6fcza6dQTTABgNvghbDuA9EC4GrJaRC0Jlp1FAISgc/kfwUsRkG5CQO/BIzB7IjMAgZgEVSAZohqWmCPAYAL9AFwWAA+qGYLuItA2A7DUuARQS4TOsESbAKQzgFewBLi83gBO6ptSthUgN03BNku0BYC04ZMWIDgNOiTFH74luGwEgBgCt2ClP+YQdQGAm8AMoOu1R7UfU0RhGoHGMAXICWJtiTYDKBwAuPbIAQgeP9zKNo2AHADEQC2XODjAuw1MAF6XIFCz9O85MQd1xGwB6Bxst8TpAeo3FdJ7IfhIiQ8EweXMhCfMNwBIF4QNQPdMbFIsI4BwQm05AJyWGvTT+1Eu/kXJf+YenGUmSzQBwAAgs6A04M4iPz0FEDrUAyyHgId2FOQH8S8XoUC/svdWhoCgkzAOLj9bj3TlRNZmfUZIAaiVzGU+AEDAAyRoQPD4/VfNL0ZVMABUEMUxfHBW1xry/iqx1Y+AIHi9EVxEfE0vDyl/8ADlnwWUlStA3KBOXs5gBbNIDhG+AG6ISAnVadEDSB06cXXpo+mTCq+V/MEsOBQK2ziqkPCh+iiIxQluHcMSuZ0nh5KcQ0BGqBx0CBIqlGvLRfofgBHyB8FvxJY3xDsMA+hQHyqUKzGskRlLSTJJDvV/5OVMh07TRnv5ufjn5bUNwmAAElo7TUkLxj1ovwVBl9jKzxMzXoov5b+cM31iE+sygmtQg48N7oFY1A37V0hVps29UpuEJAJfrg9TQS++tGYpf4QaZOEE0GGGvzKvsHRMUAg/JL1Q2nbwdI3SpKkEwUSJLpPuT2iNam3nAhBTVIM6Y4hdzTeAyHlAZtXLXOYW8/OE4DVqD/elCU06NDlOHWxAzB0UD+Iwj8AjjPkWhEhOZGIOSNNzAwhA0PUEl950edgWlfzTJkM7VD/sxG3I+ByQoD5ZyT9LUIwAckvBhIDARDCIf46iKOdDUDInlUYAYKrVz2IwK5bMID+da94UoG2LqhEEfMHSdac+6oSJF/bYxXwIEooEX5jiEtSJ6kIFoVtIECFzeMscUm8DQn5I2/YEQ9AMrjPKYI9gnEHuV2d6wnXoHSnBbKZBdUs/CcuY6y0HpgAG+SUBJb8yZoBf/3DxRSrepCkN5lUIpuiEOTlkOWr0rZMmAP3zI64mVMacIP7vv3J3oOoExMJETF1aA3TIdyt3hpqZpo8kwGQA+Dxw71VHxA1xls1NTKtDJeZWtACY0xKX0dqSVCAN9AigxC+7qfLbdrR07JYAQhu0lop7JzSF1AMI+c9nrkC95+fK/zaWqLcR84/Wigli8o27d9IOmgBQCsTFV8k24Toj5uJtGuTWBJEmZy4zuhh6rdnnz7LuB6Akk0cCP3pvg8UwLEd6iDgYjBhggg2wfqoHACX/mGwLAsqDU+1QEkRJUcdC9M5e+2hHzAIVRqY1MQUA5jskUviCPcKMCb9F9dR/QBDYFrPhAvugRIy7TMECXsGQq/3lC3bMnfGFCPJBi6gFcVA31ug/QI2bsYg+AWCiPSLfgBqrsL+GORimA4B0r7q7IqEHi34h03Aho/iP3nUioQF+DwcA94vrQw92fixSuJBvYMYZy7mTNAD4NdD5QWt5LFqmPyfZKtRYMX+PSkU8jKLexbHfWf8HwSTZZnDVrvqLA7y3WgBoWi50btGiuf78E++4Fqyw3QDuuaaJ5IjuA5GGWH6Rzvqfkj3XgnZ3A3hqmnwnEvng/atTgOfd7mfMN3FRoSJ9azUkdZta8wF0Z7n8oJioUFDsuxZczoMNpGKW1LROzNDLNhpx8Pv2YSGMWGsDyT3dbwNJHPt0o2+Rs7Mbje0BvE9kwePMbNe4PiYy76HEr2blcmgo4TmY021lOTiY8xpOP52yA37CaY8LGgyAHrqg8bik1APgGUo/S0qPi3oEAM0B+FnUe0yraAHwJIyntIrHxJYeAN1I5Sex5TO1qAOQD8pTtB92pxZ9Jnc1AIa9tAw3Abfkrr/0+juAFBLZBIA+3XVMr/t7wPEGwEQfYNtgiKcHHP4eMS0BpPzIlm7DdOL2iMnjQ74FAKtBf57IM2v8EajjQz6Pj1lnAEz6n6dxI56fx6y+HnRPAfoqJqj8cotPhk7QDg+6vW01GABgQUr6V/+xH0a3STpvNfC22YMvcZ+1KFpVqsoFieFH0b1x7ps9PG63eZZFRYb6PV2E/6Rho7D7dhs/G56ei9JOpkIU0sAzVIPcNjwdsuWMmCohyJ14yPzgvuXM06a/52TTX2uu5mR412LTpj9P2y6hZFvTVeu12eROc71ibtp26WXj6+iF1t7Dly/rIN5528ZXL1uP0UW9NmGDbC/euPXYz+ZvSwDWGV4G2bj528/2ezsAMKoEjfC2br/38gKEFYAsuIFHiBtfgPDyCooNgLnggByATa+g+HgJyAJAvQ1YM8MAbHsJyMdrWOsAK5eRlrj1Naz9L8KtAqxdxCzCKsDuVxFXAJj0nwb5W7MLig9+GXQFQNRbMnbReth17Ou4RgAmyo0ZHYEMfHe8jrv3hWgTAIuJWCEbxg9UOHmWO16I3vtKOg4wVELoTNdujIs/O4BdRQHQ5wMsldXGzOUSOtMEYQmwryyDPrk7llnNs7We2V2WYV9hDE1qsS8hk6wVuIQYIvFQGGNXaZK3zBzvfNKXkKlWLtnY1Rg6rDiMXIZJAPUvvlCm/Xd1KwWPZUkgH8VhtpbnKVLxVVhS8r+kRUXoULA5WRPf7p62AL4KJPWfCEuxWOJ4K5Dkq0SVjDtE4XXLJY4vgO1FwpJRq+TblLVNuXKXmmpHlWlr38q0Va1t4X777rIH2FAoT5TKS/mMK2qxOxwAARHi3XehvE2lCqeJLYefat1qOh5ZLNI+sbXjNkeW63QH6CtClweU69xQMNUZoC/p61Qw9cCSta4AqqSvY8naA4sGuwEwNcKuRYMPLNvsBNCv7ZzLNh9YONsBYFijuRfOPrB0uT2AXFDcN5UuP654vDUA1/5EVvDfUjz+uPL9lgD9FoSt5fuPO0DBLrmr1nLbD1A47ggLC4BB/D1HWBx2iMgawGQDyK5DRA47xmUltcji1tMxLkcdpGMAgDWPOH/Ky0E6Rx1lhGbmuPTj+VMejjLyfpgUwwBUdqijng+T8n+c1/DmzjSxJc7qI0cc5+X9QDWotN6mKZTagfI8cZ2mbdXxZf5BB6odcaTdc3mk3fPII+3+n0MFk+MOFfz+Yx2//2DNrz/a9PsPl/3+432//oDl7z/i+vsPGf/+Y96/ZAzCPzjANxDM5V8CfL43vf4xA3w6wVL+d4A/tw9Wo/D2Zx3ggwfhqhFWB/ChthxqRdUDfKAeabTHBPBpCJj4BgCwhQ9hCK8GIU0AfBiu4V8OL6LwejOKaAZQEGH0FzCiKFwTHtp/GIl2jPVUWv8AAAAASUVORK5CYII="
ICON_512_B64 = "iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAMAAADDpiTIAAAAYFBMVEWVcxbdphF2Xx/0zmKwhRP7wRnduVUiIRoMEBYMEBYNERask0hBOyaOekENERb1swAAAAADCBf+1WUuKBRGORHnqgKGZg5wVxFWRRKoiDA8MRKUeCq3kzHpxFxiTRDNlwRky2zoAAAAIHRSTlP/////////8VmfI/////7/AP///////////////////xlmVeYAADJWSURBVHja7Z2LlquqsoYxMdde27StotPuxPd/yy1qEkFQLgWokTHO2WvNuTpt/D+qigKq0Lf1cT2fL5fL6XSKtiE56pdVv7Lz+WpfHWRX+lr4TU4jFGoOrgsE4Fprv0kPiMH5el0OALX4m2bww44pQPDibzPfqiWYMwDb1F+eIUCb+p/NABQA1019twxcZwXAefP77uOB81wA2Cb/ks0A2uT/bAQMAdgCP/8BoUcANvmXjwDajP9nOwJ9ADb554SAcwDO20uf1zg7BWBb968mL4A25//ZoQDapv9nGwG0Tf/PNgJom/6fbQTQFvx/9nIAbeb/s90A2qb/ZxsBtOn/2QSgzfx/thuQBeC6Rf/LWg1cYQG4bq90aeMKCcDm/lcbCKBN/88mAG36fzYBaNP/swlAm/6fTQDa9P9sAtCm/2cTgDb9P5sAtOn/2QSgTf/PJgBt+d/1j6smANubW8vQAmDb/1vPGNkbRNvVr08YF3UAtgDwMwJBtOn/2QSgLQD87EAQbQHAZ4cBaNP/swlAWwDw2WEA2jIAn50NQB/rAGJqfKwTQB/kAMYk/wwczjIArM8BvFVN03SHcxTWo8qoUZE/Qzne1f8J9SNrdwJo1Q6gU7FMc4yI5DepQXBAOE/L1wes2Amgle4Bt8oltfK18LWoh5viID9Qg1BzkKwJg+skAKd1iB+VBQ6D7AYwsiDERRmtA4LTFADnFWif1NqDSE9hUFOQrICC8wQAC1c/KnNU3ayNCuWNKVjyWxoH4LJs8cPgZn0E4bIhuIwBcF2s+klhc+YPLUGRLJaB6wgAl0WqT6Z+dnM8stYQLN4EoGUbAKI+rm6eRoUXycBVCMBlU/8TGLiIADgvTP1UXX2S5KuX9WQU9UDNn+VF8SB/gsIqkE4X9hlIF8bAWQDAZUHqx0leqehOVH8UaZIk/c/BzV8mUXIiHdtP9d8mZVk8coTUSKjyRcWEFz4A1wVN/iKUlb4K8SPtyd6o3I0OgDLhjTStQWjzyDIjLBZkBq5cAC5LmfwpCuQW7Lie8vVPdMqTEUXJEIBkbKRFjgK534fSpZiBCw+A64om/0jeVhqAsh0vCmRswWLMwJUDwGUJ8ic4k83UCYQ4KVmAsodB+pDYYshwsgQELhwAFiB/iiZ2cCfE1wegTNMGAxkIiCeY/cscAjD3NeCk7c+CZjk29fI1AWgYqEeZlOnkfhPxBEtZCaJlnAOIo0c1bvcfkgsxQwBaCNKpDefqMXMETiwA1wXLH6BCfntOCQCu/i0EtSEYZWDuCFwZAC5LlV9JfTgAGgaKUQbmjcCFBuC6TPkzRfWZdaAZAM0YZWDWCFwpAM5LlF/a71sEgDAwsiUxYwTOFADz9ABxXFTiLRjN9Ds0AEX9f7k4N1kVM10UXigAZrruDy2k3DQBSMUWoChGzUA407xAH4DzHOVPkJVsmwIAUh7gxUCORNEAmmV28NwDYH4eIG7F4W69muXbLQHQmgGRJ8AzDAUubwCu85v+RXCwtN1ysgUAYUDkCQ7BDEOB6wuA89zkT0J7aXY9AFIpAIgZ2AmePZydHzi/ALgsw/rDuFILABT9UQcD4TL8wOUFwGlW0z+tDjYjKdsAEAb4CByqea0HTk8ArrOa/shyIA0PQDEcIiuAZmUErh0A5xlN/yKzvY6SB6DUB6AefASyOQWD5w6Ay8ynP3AmRQeAVB2AQrAimJERuLQAXOc9/cEdJzQAhXhw8wIzMgLXOQHAn/4Z/G6KQwCKYpgdzGZkBFoA5hECxGngaOUEDEAxPh5DrDNi1eYSBKB5hABxjJ3lTjQA0DYAxaOOBqtm2tNGAM/CDVwaAGaQBYgTTrxkK3sqCwCEB6gJqBEgZ9lZV1AlMyDg1AAwA/150Z+1vNnJMQA1Ao9waATqWND/mycAXGdp/qvS2utxDwDPD8zDDVxrAM5zNP823406AAb6t3EAMQJojm7gXANwmZ/5D62+GGgAZK0Axwh4dwMX3wBwzX9u1zTCAiBjBR6dHyBGIJuVG6gB8FobOo7Cg0PvrwRACQ3AIy921Y2tO+E3KXS6Ip8xYO3+D5lD78+uA4EAkNSfENBEAn0GMs+BgFcA4jJj46LARYpMFYAUCgDiB3BACMj6gUAZ+wTA3yIgzj3tlDkGoK//I3/kAwJuD38EnP0BwAn/cjcRETAAKvoTAh4ooxEgfs8fAJ4WAXGM2PAvcGUKnQLwYEeeD9zA7YB8LQYungCIo8rfQQkpAMz1b1Z+D854uYGsFwp6Wgx4AoCjf+5uDpwAAVCY+j0bkNergXkQcEE+0gBxwi7+Mpcb5GAAjGd/xwDIHzijEKj/zcty8OQDAFb/7OB2LQwFgEzQnz+nPK1//Qd5NQcCfABAlv/0eXnH2TA1AFQMACUxZ9B/GbIEeEgInJB7/R8398k/GwDw5c/HB/X3HQHv+eAhIeAcgGH6J3f9rWUAUPYAk9LzaEAZQ4Dzd+EcgIH+PuweBACDuZ9rDDYU9EAA8qq/p60QAABMJ/9z4MozAcjr/D/4Wf2aAlBAyU+GZwKQV/sf+sl+qAAwMf15tn9Hj3kTgHzOf18ZcEMABLN/NzJGCQh9EuAQAHb9V+sfRXMAoNT1AA+++Og16n+UYYAlwOVq0B0AcTkH/ZuuIa9HevYMOjHijwIw0J8vfm9gPAEBS4DDlZEzAAb5/9zL/I8bA1A2V3dxe387qwUi67i0LGU8AGv+J8R/MjCOAGIOibhbG6GP0L9tI1DrnpPecBm/IVj9x1UVYpw3zcUIBSkHAGb6D8X/pcfADsyMAORq4nnT/9VRXroBGGk1hjoMBPpz5f8VDgkEKAKyW+ZqfYQc6V950f+pvU5n4doetBSUnPlPG/8J+XsQtAjIEOAqQ+IIAA/6tw3lNXuKP6Xo2g4+XUFffyX1XwhgsRVAN/qEyIoAiOkiCQf7+pPWog/DhvLPwLy2BLsiLWn3ry5/h0DTtpZPQEgT4GaV5AKAGB+crv+aqV+ZNpTP+iMIcf60APr6vxGQIeDg5KywAwCYBKBl/cFaivflD8j/JyFBF/719R+KHPaHmAAOAgF9c8yFp7QPAJsAsqk/sfxADeVpA0DGk4GX/jz5X8L/6wZhgMFgxA0wBDhICFkHgE4AZIcwtii/Uktxef1bABoGgpoBof6U8tSgERghgL496iAdYBsAdgFobXXTNJXObjcbAAS9QeKBX578QvGfhiDkELDjnQ9w8brcAYAOLr5Q7fmVJn/j08OwrUxXNcnBTDD7GQBqBOqf+Ef2eaTmfh+C3g+ICQh6BGT2N0wsA1AvACgPYMekSTWVbqWtw3n8KIom6x89t4MjkvtPH48cNYniYQxIWYCGleDvFynq38YDFAFDN7DLcUYRYHspYBeAuKAFsBLUjHQX6tsekt0lor/2BQXbwWn6wChoVpFi/W/kn1X1p6wAEhNA35m3XEXGKgDsDpCNZc1kT3HSWBgXyavB5Ck5nSQOhBR5u20k1r8e/15x/z/ZwSFgxxCAbg6sphsAKmoBYMGajbWW68TnNZQ/jQDQHgZojcEDNxCI9D80CCioTyOAnwgwUQBJCPVt12IBoCoA2IhnJox/1ok//MHTuAV4nQUgzeJbCOgA4DUOhxoBRQBYAhgTsNvhnF4KWA0DLALABADwC4BR+QM00lhWDoBuB6hMi6chYPV/IqBJAOKYgBoHvKOWAnbDAHsAMAEAuCuLI3HkP9lSXNICvEoBFp0zGOpPCAj+KRqBkTiA/DPOsd135wYAel0OfP87jh/83lJNU+nJluKKALR7wKjq+f/n/G9GjcA/HQQ6ACgj0BCwo21btUAAmBJAwAuAuAyFjUVlmkqrA9Aog/4FN47+BIG/0IQA2gSQPwiZ+7NLAyBOLe4AifvKkvZCMr9qFADmQGi3B9ztAPxy9ScI6MQBCPVMQMfArv0TqwbUOgDMFkAAGQAKOwsqNJWWAWBoAIgN2KHfP7L+Y/UnRoAI+/d1bMbXnxwBbxPwNAJPt5A52UOxBQCylgGMT8i8qbQCAJQB6HaA/prQ78CO4Hi8/7zG/XicJgAhxgvsnvpj5GQX3Q4AzAoQMgAQdBasHkpNpU+KAOQ0AC0C7Ljvf5hxP/5NhQF9AHZ9/TGmwwBLa0FkxwFkluAVeP9KtbeYMgCM/hwE7j/cUVuBFoK/PwEBuGcC+vozYYClg+LIvgMADADiMoCQXwUAxgC8939+Q8oJ7H8E4x40BPz9EQJoCoYmANMjs+8EkH0HABbAxpzqwrV+OhUGxwAQG4D+GYB61Rf+eyFw/xkZx1b+WvyWAqEJwOxA9p0Asu4AwJaw/M6Ser2l1AB4DD1AuwNUIzCtPyHgrzdYAl4mgDMC604A2XYAYEksrvnX7SwoDYDQAzxDeRIKTOg/QsAUAPadADwATAoIKo3NM/8GnQUnAeCGgL8DAIh3n9RfTMDvFAHIdjoIwTuAysIKMI4RbGdBFQAeHAPQA+D486NIgIoJ6K8FD8cFWAD6GhDQIXBOcWnD3kKSAEx5AGIAfqTGH98EICoZxBvvb77/2f/GcwcgTiw4gDgJoDsLKgEgCAHbcZcD4P7HR2ASgKfpa37PHnxjGByAEH4FEKds8s+8uvTIkTAxADz9jz+SQxAGvG8Nj5qAQ/sh+7+ZA0CnAGBWAJzwz7yv8BQAEyGAsgFgTYACAPVasJdmgk4GwALA+GqQPaCh/hD9Nk/CKmEiAN4eoB8CShsAYRyIpnwA/utnGY+ztgD0PRAQBzDsLQRSXVYOgH4M2AdAwwAIowA0YQIQzdgeOBkACgAdAVaRFf1hisurADDiAf5+FEYgcgIjAKCA/RTgOBAWAASduh7qD1RE0QCA/t3vowoAwjBQDAAnybT/N1sA6BxgaEP/AAp/IQDTeUDNEKD2AaoAIO7H70HzgaAAhMApgIH+cMWl5QF4jAFwVwKA7wKQAAAkoGt/nCkA9BIQw+sPWlxaBoCCsgC8NPCP0vjjh4H8ZcDIFgPkUhDSAlSwW5eD+Q96tBwEgD81AIIRABgCiHMRnjE5ztIC0MXAHzPXXx6AVxqAA8CXGgBHWQCI9d8L9f/ZA74KZMcAVOD2PwNOgY0CkI4C8M82AMG+ll8IwD6AWWEDA0AbAONANc4Z/aF3QQQACA8EuwPg33G/H9H/ANtRAFkxAKG5/je7+nsBIOBHgdQyANXy38UA3AGTbKAAwBoA5lSRjeuxJwgA/oxWARwAGvnvQgD28E1FkA0DYJquHjQXtnA9GgSAf3sV/feCZeCrmHy99CPyCwDY/xyA8+yAANAGwFCvOAqs6z8KQCoNgEEiiAWgcf73uwiA/c//qGMRUCYAzdEAVPb11waALgh1hACg9QBE/qMQgP3XiT4XWc3KAsAaAORAfwEAnHvBj5YAPgBKQcAhGAGg1v741H8AwP64i2NmsxXIBKDZGQB2AWDpUqQ6AOh1JUjPB+wPAgLqj/477smdcj4A+59dm1e1YQJAAKB3AcxmLFtc3FrJdBgAFHzA/cAQ8NL/j1h/MQC19X8Gx/AzAwaAEMwAMAGgxeYiYgBSBQAUfMCBDwBqYz8RAPuv3XsLjDIB4WwAoFfthgbATVkENQCYIEDPBNwPLAHdB7RLv77+TwD2P/v7rr8DSpsAkHMBIAAgOANABwAWmwvIAJBKAPC3l44AWALIjwfdyv8+NAAEgV9mUxXwVcMBAIglEwAEkWMASg4ABQMAWxj0KO8AGAJqetrEHxeAfeP8Y3vGFg4ADDdnKysXS9UAYLsETgAgR8B9CEBf/mEI8PNz3HHOv1DhFp4FAHQ5AKPQlKktaLeJ9kkBgFyYCpRcCu6pamJP+X9e+g8swM99xz3+RC24IAoGAABQQC1OmcoillslcAAoxwAQBQEy98P3TD25ehzvzZ4/1wLUf/U/obYV7EoQAIAQaNXOVBax3TlTGoAHYwJYAP4mCbjTBaVqAIL7T6P/nmcAeM6fHyaHMwCAituMbBK9ArTeMEsEQDoFwKA2ODHnE+dA+gAEh+DYyb/neIA93/nzp4n55TtzABCQ1WbOAFjulHIapoJLSQCGDSL+RiPB5hzQm4CAzP5Of44HqOUfn0VUoIS8A0ADaTRrK8vdRTjj1TSKbwHSXqv4PgEDAP7EbuDeRf2vwuLtTV++/vWy4GvqHVKrbvMw0BiAAsgl0fdKK2uaN8Wkk7TIMUbPtnEIo/xBOsUndLP4DoDHBADdqu54F8v/JCB4FpTiAXC877/+m776QAVdhXcAgJ6GSQHZai8XR0nT/oNba7ppLJb2GOh1CycEvLYDuADURiCgGbgf+4nfoF9PjhMB1PKPOn/4OQcBAGWPKiiQrKwAJTvKVyEuno5ABEDI07+rBNn58vp/2COgQa+cHE//+6+sPa8Ap4opADmMbPSJkspCeym5nuJZawpQnpYv/ftBwKgJ6JUD5Y3jntafWQK+Nn3V8mW5XwDAYISvLELN/VS6p3jbF6hh4LUMkDcB4hH0vMPAAdTOf+fB7JoDQC3dDNyRhcoi/cmv1lO87RdaM4CLbj9wuA4IFQEI+svEwRLwftzp+0vDTWFDADBI6p4+Bl7Byp8o9xR/NQ0mZuDtA0QmQEJ/KktA60+s//8SA4eJfQJArd31PQB8ZZGX/CW6KY9+4/AwJxZg3AeoWP+B/rXz/69el+pPmMqjC6A8ADIwAHYOgch1lZ4goEEgH5iAX2kCAqbIU1//ZumnKj87Y8x8AALzAAWQAQBLAejKz7SOz4IagVdXV2UAmBwxPf/3x1+ShjRLv2F/AFAeQDspSW8CQEWAdeiX3W7mBDQIoKETkCPguB/Rf3/8+q8tWGmUgK+8uQAoDxBaaIoQp9WExFUYtv0YMhRWVZYJfQBpGl3hx8sEyMeBAZscpvW//0uSk47+kD4AefcAtAGAOQYu7izZNBXHedG89vhdKjZN8x3qUsRkDUgDEJBQgCVgygYER7783f3PY/2phab+gD4A+fcACL66sHD69zvKc46EkV7xGWsB2tbxtRFoAZANAwYbxPseAPt7QHwLinQBAPMBBgBQ+zfaHgD+wlsc49Ge4q9fQQHQFQlPyiInDHAIyFDX2Jd/MkTO+nfX/4/tZwZplABMG5PMqQkAOYgHgL7vFkf8vtLhoKM8bQFeZwHKstjRDHStgrNqN0KAnPzP6d9BhbQBKID8pgkAIcAJfnADEJe84L/CnJ7iAgCa0ewbDgnAedvb75d7Oux13Fuk/kv+5ycGpTbmAUzqRB8AKh2l/QiUuQYwANzWgoK+siMAkF0AXA0ICALUNffkE/CvO+7NV5/ov79/7ar3x2U7iOlncn7SAIACYOrSJ8oAigtihcaigxiAPgpEIfBSLBwn4F9z3pcnfiP//mt3Ou1u7w70VaL7TR8w2XMDABAAgtSEhS8uON5YVAxAdxAgLdBrRTgggB8JHgey9+U/1vL/dzr1TUAeAxhg5AOA/iIw0PYAFWQOgKP/WHMZIQDFezxCjg3oCrp1CKDeLbG9WP77z/H3PyL/6ZT3AAi1v2wAMnW0AaAWgbqpCCoJZJwE5DQXSccO2UkA8CjefuCtWWcCnikhhF7WXyw/cf6n/xr9T2X19gGZbh6P8nb6C0F9AHKAZCTYpQK+/hPNRVgAUp4FeBQPlPEJwP0jYr9/rwqPA/F71p+M5IR7JgBBTJ7cAwCovwjU/IxTBrcNONB/cm6JAKD0r0eBAzEBLQSorfPAV7+57fGSn2R/y9cn1R+q/b0DiCBAF4AY4tdD3nPTaC7RB0DgAZqRF3k1SgBCrzoPvNFa/7f8SRKhZ3Yxy/RXUAiikoI2ACWAAaJCQLNzDXTHWrneUgIAWP3JVvArFhxGgvV4V3gUyf8a7Z5DVGSd/OTECcT0KZ0DAPDb6dOtkKVl5JhkABAaADKegcDbdXeRIMa/x/vIaJw/LT9Z+ofZCwDdNTTIHNQHAMD+wJ1vZ2vLZVJITgHQqN8dCM0fmM0JPvu6achfA5u99NeNfkG8sH4QWAH8cqhLBUxlAdm8FB8Aev7n74FpL1B1xf3v96PY+v/vv4RW/5n4S176Z9qr+P4k1M4EaAJAWW/NyQt1qYC9Vyadl5QAIM+FBGQVsf5MhcfeIOd9dwmt/nvzP0bvzUZtF5oDTCBdAAqAEAADbQMwGwDSPvU0CsBA/wEB4Vd3rY+DADEMuySh5T/1X2APAAwQBBSOAcAAGbwKJgvIVJaQj6l6AMgYgB4BLQP3/XEwWn/QyH9K+lN/cPKnMvYBlOfDjgEIja03zIEiNpRQsUejAPD0pwg49io8DjC4f9HiDw9+1Q7c3AeYq6AJAAR7MAeKBg5AISDhATCu/y5/uu5eib8BA8T5R6Pqt3brDUAee7PDyHz2aooXw3gAxgGo0DgBQM4ZOA+JbsGezfz05G8v+4yJP/ABmrupEJEYMv/NevEn1H427QCUDOEbgIEH4BuAHO8wOc/Dz/s2LR+OtfxdzaHT5CIu6+6i656noNZihVMAsPFOEHWixeBiMZUCVLMkTwBSKQOwa08D5v/uza4fF4HG+Uve9atfQKs/IUD3BQTGnlgTAIAYEOJAEdtfTG0/QQwAV/9GfnRkr/f3TQAp7q/y6N19pEzXBALogHyR1zfdIdC9UsVHGQIg1r9J++U4YM/4MnlfRfUyw0QegCVGxvNOz/fA7GTQh8pV95OkAdjlrfx/zYHPPR+B/f1XzZDV3iszDOH6sZimGdUDIDWOPmH2MmkDkBoAQJUGZfUn1j/P31XBOQjs9/JFnt5zIHvVpsrNp1HqEIDceAUHcpqB3gRU9kUDAAqqKBStPzqOnfb/kSvxxyRTjDfUqHxM7hAAbL6PD7GbSBkAHRK5ADAGgOjfOH/hdZ/9ZH3f6cfXDQIq02BMD4DQGN0E4kBRYnqxnAaAawCI/DtuT4g3AP+LdN1gZppNQaahNDKdvtg4etEOAcwvlr8AoAwArX/t/IWlwFsPgCA8mGYsjU2NiA4AlOcxf3DtM8Xm18o4ADCHQFjnzykHnemfyAwgJ5JeNIZMydWLPSH2sQCulVEADA3Ajiz9puQ3Oddr/BbM12PI8Ldmp9h08mKIM8V6GjwBYGvDP5f/+URDqHubzQ0BLvfozV/qZkXqDADjVSDELgZlhzSD6DEAavmnrH+byjXYzzfeUzNfByJDcMPYzzdnzgFoWpEOgJJrAPCo/Pt78Izh9c90mc+DvhfBzgAwXnuYB68RxJnimAWgr/+o89///O9diSQD+Q7YGADkDIDQ+LGR+W4iwJniPgCMARh3/iTv23sLIGe6kPFUCl0BAMBtZX6iDKBIIQvAS/9x59+2dum5sQziS1R+bKkGAOZpAIAUNsiJsgEAXfg3bv33bd6XuphTmZ+L1AynTRMBpgCkxouA1DyXjIyWYdmzPUxnAEat//7n6/mayZku0yAkNV4GpB4AgH1qzVcHUSOJBqDR//HL1nceOv/h5NPNBVEHK/zMJeQBOujtZO0zxTUA5Ezm2wE8sITz51jCzNt2rrE59gMANk8Em58oi+O2qABJBDX6P3Ip58+N4XW3c00XVF4AyE2/N0AiwXg7OY52X910P36hokbg8Xvfjzp/1lkBXM40Xwf2Z0LuCADzRGDoezs5jnfH/f4t7v13yvpzOroDb+f6eZeGFiD0lAYw3EaJT4NWHnd55881v+bfozIGwJUFMDXgEOcJjJ4h3v3sf+TH/kfQ1BUgkWe8n2/6DMiDATdPJJjZkHinIj/X+oPNX+8BtRcAzFe/fYRUl+Bq+o+19O4nIzTlM86ILBIA829tkP6ITyry78fO+wKkxMznwtIBcD5x4uNe3vmPn/cFNmWLAaAyXYKbA6BvexUcgNj5Q3giKAByszgE+Xhm0MhH9VsfAZw/2HrW/8tEC4TWJBUhawBq5y9x18t0ET4Dc+oFAAx5pEwRgK+9lPP/koosAFKavgMqQwDKWGfkh558WuP92g652k9KeQDi/Gf/TbpRegUAdUWzlUbe30XT+QCc9/cCVT5hh2Xmf5Dns/8mrw9AXgG4HTR6cx9uhh9g8AmHaf3rzzsc5v9NOD/jA4CFjew2Jf/9tuBvtwEwPaYAuGUbAJ8NwGYBVADI9MbN9BP0P2AKgOV8k+EneACg0Fi5dqV5nq2dtEb/Yn10AkwEHrW/iWaZg1D7m3Sj8ApAGkfKC1c2jRM7/ISpRND+S+3T6DSOzjcx/IRlZgJ3s00F73dqnwaaCt59TCp4vptBR335PmYzaM3bwaoG4CO3g1d8IGR/VPyoDz0Qst4jYYoFj7YjYes6FLpXjcK2Q6GrOhaurP/HHgtf5cWQ/Y/6KuxTL4as8mrYUb3g4cdeDVvf5dC9RrX37XLoiq6H74zrXHzU9fC1FYiIYvMibx9VIGI9JWJ2TYmYSPOnI+POh8svEbOKIlERQKXfjyoStbYycZF558PPKhO3tkKRkbn5/qhCkasrFRuZr0Q/qlTs6opFR8YrOE0/ttRi0WsrF2/e8+LTysWvpWGEEQAA/SoW2zBiLS1jjFxAZd74brEtY9bSNMoAACoPUX1a06i1tI0zsQDVzXglu9y2cWtpHKkPAGUAsk9rHLma1rEGAFQQicilto5dTfNobQAo76O7jAHZTvbTPHot7eN1AaCdD8jjL6x9POx2rnbzZcqGarwAbQD6OQB9D9YPAXxtJ2sCYBx70uavBDEB6gsSTQCor29gAEpjNwiwHtMDIDFfBpQAQQATBVSuAKggIgCIOUAtAhJ3AACsXyDOdA1MgOqj6AFAOwCk/+wAJ8rMV9PI+NlD8+MUmf4sSjIDJ6AFAO0AgB4dxb50QL7Io1IpD/1plBsUydEBgCmRlOs/OcQLMLfEmgCY7+ZBTADWlShXi9ABILxB7AODmECIPTVNAEqA3bwKIpnKWGS1eaABAB0A6B4EiYBOlAHkU5H502Pz83Da53qHkuSxTQBoj6MdALPi5eZHInTnkOYqACIKLG8wPoB2AiozQRkAOvNk4gDo9UvpLQbUBgCAvQjGB7BOQMGfqgLArDkMHADjAQA+AzsGAMD7ULb7YWACGCcgT4AiAKz+2OSZHwAnygAiMW0AAHbzIM718iJzeQLUAGD1h3vkFCCKStwCALObV0FkVIdrc2kClABg9TfxWjBnigF2E/UBgNjNo0x3bjSfSqZqspxXUgEgLpka2aXRA+cAHsB8N9EEAIDdPHoamLxPdnkmyZMCAHq/QCoJon0uHmQ/DUHMuRziXG9q9kYx024DyzT9kgUgZuLM2wGbPW0KcaYYZEddGwAI+0N9BaOYivgkhoBQQldJAOIoZPRHhg8bQkwfiDM1+kEg/es1P6N/qt0oDOQRkE3aFEkA4jQD1r/v+/RuVpABEQIYAJADmG8qHWZmVTkETLoBKQAG5t9Yfzr61TafKUhEog9ACaAd9SWM1lV8Aqp0FAEJAOI4rcD1p1atKcC1IoMlCdL/Hr0XE2ifiqjAAmsuATc8qu4kAHGEb9D6M1eatF9dALIpgQzeNsC5GPPrXVMEZLnYCEwBEMd5Bq8/0LUyoPMUBgAUAKl88+tdI3bxydVDpPA4AHH0qIafhs2fEeRaGUiVLDMA+ghqr+EoxcxNwDBh80QgVgMg5stv7qYYA6DNU38lmSU+AKAeQf9uB3Ww29wEDFO2LQI4iYcMiACo/9ME8+TPSoAHfIBcK+svAk1SKAhoshUgdzsATMAwa/N8S0XEMsAFgPxHheAjIoD5H0HcKwU5UGQMAMiRHnATwFm4P80UahiIxQA0f1uggP/zOIZ4OhADAHKgyBQAoCM9xpe8eemFStRcNczLrjnfG4BTJ339Z2UeihrjVinMs8EYAIADReYAQJTqY0905TBvOcIjHXZD/EiTRvL8WSw6jpL0gcORrsg4gnmyHORMGUSRQgAAUvArUubpwEkj8OzTW4Vh3vzmDIdhlY13xAaa/syyF+hKXOoLACgfkMKus5+vOp/scn6Q7cqdR1BPhWEMAJgHMAMAxgcwNzwToHddh5cIpis7AnwkoHulYB7AEAAgH5CAnbVklgMQCNTywz1RCIM6nAcwdAGUDwD6PiZ5zSECpSECqIwBH6cAMgAJmAcwBADoaD994LaKAAexApmu+hnk7GdzQCYT5gEXNBkCAHS0P8aHDD4OfCIQ5ZWO/FUewcpPXacyOVUIcakAyAWAHe2vwE5c8xCIU6zIQIXTOAZ+jBLqYnkCaC8NAYA43z5MkFawb741A6U8AxUugSf/IAdokvSGu08BAAAUjHR8jMHffrvF90CTEFTokcSxjd+PwdY6FeCq2dQFUMKZ3PKn7/YkFhRoN/qSAqMqY7NATUq4QrhIIivqs2tdEy9HrSWMF83GAEA9DR0HVpGt0W76kMx/jsN2KgX1Pz53B2Jrv7gCigDB5hwQABHY0X6wNyRJAbUZZFV7UL7pSwWRbwDgjvYzdR4Kq3r03XIWOfhNBVRlCZhLBZAAlGBXphFMAT51AKz/JuZqOQK7Cl/6BwDmntvwq1lYC3oEoIKrLJDD7psAAFBApSUYO4njtQDAnFEz824VrJ8EAICauEaPxLyoR7wOAOgslxnY1CSBeHIEzLehUaocZANcA8BkAMxWuJTDhbCRCPoLpoClXgLb0rgAgDrBb1xaJoWeIAjiKyKwhQlzsSdcAwAhZGkZBLoGhAIAEEt6LQjzHb0CAPqFAI0tJAA05IZfkTaYhzxeNgBtshHKqVE0wZhHGAAKQBNQwt/G9AcAe1e1BDQAxXwAALrvxn9nFnPC1gFgMhumNIPfowQDAOjCG9drWswJ2waALS4KWVsKKksCZAEgTQCTOLVIgGUAWP0r4xpIFo7OAgEAawKYlbM1AuwCwOpvmtWwYgDALACsCUgyJwRYBQD8S1gxAGAA0CbAdIXKnA2wRYBNAFj9gd8J2D4JmAWgTEAIWknNGgEWARjob14DL7RyeQYMAFgTwCZQ7BBgDwBWf/OEliUDAGgBKBMAX/Ivs5APsAZAXGRWiwsCnpmFA4A2AQAl/9iij/A5QVsAsA4MQH/ot2vDAtBXH6MFEGAJABv6R7auzwICQOc9AQ4rsATULzKePwAx57GBntRGdhzSAkCVPxDbgDCK5w4AeHOJYQ4I9JQEKAAp9GMOCAhAFwMWAIiTAF5/ZmqlcwXAQqWPYflvyJOi8AAw5z+h9C/sHZKBBSC5QYcq6m1APAJgobnIMLwGPioLCoCNSh+cNiBwRbtgAYiTyor+YJVFHABgodLHsAA8WE4IFgA2+wO1cGUri8wZAMZbVRaqq4LWbQUEgFedNoevLgx+QAoYACuVPgZt224HGDcACEBt/llXlaWAlFo7KA8OQGLhbs9gbQUUC4IBwKtQH0B9d7uXpaABYHq4hlA1loe1faoyngsAccl5PKjIIoTrWOsGAForoPx9HCMLFdxhAODWpofKWtMBUBXNHwD2NA+UzeJ1gwqKOPYNQBwXwc1S+DdwACn8ljg8AEw+EKzOQ1xyXnRoVMvVHIA4TjjthQKwSpf0CsDGRTkbANCVPsDcVhwh4E4exgDwO5OgCDZTBd1MwzYAkBWRmOmWc7s5xLEfAHiNRRvzD/aFHdTNsgEA4wQAb/lz3cBIa1CbAAg6S8KZf/Z+hJ2b0nYAiDJLTy7oBqWJgAEAAvmhcpSceWTp+oIVAFgnAHmWi5NxH+sOawUAUV9Z2JOrjMOzdEnWDgDsBU/I+u/xCUGV99cDQNyAAJ0gv2fppFSGLQDodBBosZ84Tituv68MKy4KdQAgbYW5NuhQpZBHFpkAoIqWBQAbwMLyK+4LGSq1eVAGgLSeCO12lhTY0NTWDWlbALA1/3Lo7huhsNGLfLl/NQBIwwFh85kQustJ7qhopjUA2Fv+KXQbmEcl6vsYPiSL/isAQD7wIYLuUD2gD6ynNyvpVKcA0NfjwC/31X5A2A6s6xMOBcBoT3ESe4BfLbH87pwAwK4F4cOY0b6QgUTrFykA2lYzgYvGooIQ2mrpfIsA0GFAdkAWWkGNtgZ99orXB2Ciozx0Y9F3ANg/W2u3arZNAOgwwEoXkJGovDMEHQSxKgBxJ34w+vFhGtu4tEzpb7duvl0AmFvyuZVmYOlUd9gg7JpBsRxwAej+u6TAE+LXsz+10l4sd1UlzToAgzp5pZU6H1I9oqsQ58/GUE8W3i1j+n+cpK92Us66SoszgLZ759gFgLVmtmr9iLJzg6ggC0OMi7QmoRH91TSq/tckTQuMwzCT+yScxA5qS9nunmUdADaesZXRVG0QnNWjCrt5Xv8v+XefbYUFCwAbkbNrAJgVjbWcNsnS6vcJV+spnlrrMefsdTkDYGDSLLYAGEvVgo0m1WzvK4QuXKZTAAZBjU2jRpI22CIDFU6sNphkD7+X9jun2QeAXdZYdmtqfcLV1C8jy+1FmZvQuYPmmQ4AYC4L3awHNk0GpwKNB7Iqt63+QP8DdqC/EwBYy3awT7Zkr3jJqW+rozxrKQ8O2+U4BYDdGnZi29pUrikEFZrYT7DlKV10TnUIQOSBgA4CktPVcgfZM4Ps5lHzm+MFoEsA2IPizgjosryEAtREBYcp2ZvcYIWeuwfOnpKtju1If1cAWKierQpBl+VHTdrvLfb7f5vkIOrtGLh8QCfV0X0C4JmAHgZE2CStxw7nYZvWxzvy70n/v3D8ZN70dwfAICF0QM7fMwNCbzPIk/CC9b+LBJB7AAZFFP0R8E5QNNPt5PsxWP0fDl8McvlFh1W04zkAEHl9ithBXfyZADCs8hF6fvczAGBQXNpxcIQinwQcKr8v3z8AcVQdvAbHKPJJQAZY93WRAJDqspnXxRGKvBJQv/4y/lwA4jK7eV4co8g3AR4SAnMBYA7vArn/1g8bRT8XCACnvOjD/ZMg94vggd07IF8S+AQgjtjlnw9vePIAwLCr7sFTKOgTAFJdOvOV//UMwHBfAKqy9nIAGFZA96J/DcDF0+rXXnW9BQDAqXjoKSNy8QMAjwAPgYAvADg1T31lxHwBwMmAQ5ZYnDcAw3KX/nZFLujsdxHu1Q14AYBX8BZ7S4Wc/QHAKwDv2A34AIBX8tpfKqwG4Br5I6DMmET4LXC6GvAAQJwy5j/zmgyPrj4B4KyF3aYFnQMwTP55y4G8AfB5HiaOwoOFXkBzBYDTW+jg90jE6Yq+L5FPAjihoLtY0C0A3HYH2O+hqMu3ZwD41b9DR1bRKQC85jJZ4flYJAHgHHkmIKl8TQyHAHBNnV/33ywCagCukW8CuO/GRSTgDgBeZ0Hf5r+JAWsAviPvg9sEAtvXxRUA3Orm3s0/Gd8EgNMMCOC5AdOugHMBgN9Z0L/5J4uABoBLNAMCeG7AsCvgPADgdxacg/lvYkACwDmawxikyBz4AQcA8HtbBGk8i5d+bgC4RvMggNsXMntYlMc6AHH0yKx2ljSOAWcEAPGVvLdVpdaspWUASHMjfmuxmejfATCLIGDECNgpyW0dAFEh89lM/yYEaAA4R9G8jYC1usz2ABBVsJ7R9G9CgAaAazSfITACdhCwBoCwgPmMpn/rARoA5pAJoBznwREClgAQyX+wGM5oZgE6AC5RNCsjgB0V6LcCgLh9AZ7V9G9DgBaAczQvAvi5E/gWHRYAEDcwsZ3V0gsBWgCuUTQ3BIqAX9AtLAArtkIDQLrL8dE9BMXc5G9DgBaAmfmAUT8A2awBFoCxphVzs/4vD9ABcI7mR4C4ExBYuxZIAMba1qBkftO/8wAdAN9RNEcExC3hYDwBGABi228zj2U4vvsAXKJ5IlBUNns3wAAw3qWiKuYpf+cBngCco3mOOHqIy32HplXcAQBo6tKLe1dWjyie6as9UwBco2iJCGRyTaJtAdA2lc6WKH+3BngBMFMfMI2AbKNweAAmWorPXP6nB3gBMF8TMImAPgP6AEyqP3P5XwbgBcCs9gOUEbgFWvGAJgCt3x9tLDx3+dt9AAqAcxTNHIFivE94FuBUsceDOgDN56c4GG9BQhapM3+d5wEA39Hcx2Sf8MN4s3hTAN4N5Q8eeopbSQJQAFyiBSAg0SRaAQJ5AN7i+2oqbScE7ANwjaIlIDDlCeh+T+NiyAAQxwqdp0C3qlyEgH0AlmACoq5JdHCTGEFNQRmN9QIZBeD5g2Wtvdzvs9hU2poB6AOwCBOgYAa6lp8IF+mJ3xXmCQBH9/o/PKXPVmMyYzGTnzYAfQAWYgKeCzGVRuFZFoa4BiHpK8zpGdRImNTC4zDMFJoNNi3FFyN/3wBQAJyjBY1mOabcFpR0hiMstI3CStQe1G1aiGGiOukpp95UOl3Q5KfWgAwACzIBTwZKm83i59FS3K4BoAG4RksbfhlYovp0BMAAsDQT8GIgDzPX4mdhvkj1GQPAAHCNFjlITFggh4agQsWioj6xAWAAWKQJeDIglakzH89M41LfFG0AWAC+owWPFgKblqBCyxafjO9xAM5RtHAGpPO2qj7fdUd5+0tAHgAzPxcgT0GTwQXBIHvnlJf/bk7fUwBco1WMbg8nzXHYZHMPqrI3OcIqxHkqsau01AiQB8By40AhBlFZc4Dkk3wkXYhq5ctoTdLzIkAuANdTtLLxTvM3Od8chW3Otz9IhjhEeZMhpn5kVeN0lQBg6XHgJAhcccf+bj3j/C0DwKqcgB4OKx2XbzkA1ucEtiFwAHwA1usEPnucv2UB+BAn8GHj8i0PwEbAp+gvAuB7e2FrG99qAGxhwCcEACMAbAR8hv5iALYw4AMCgFEAtmzAyjMAUwBsgeDqA8ApAK7bm1vHuGoCsAWCKw8AJwHYCFi9/hMAbASsXf8pADYCVq7/JAAbAevWfxqAjYBV6y8BwEbAmvWXAWAjYMX6SwGwEbBe/eUA2AhYrf6SAGxZ4eWN6zckANve4MLGSVJ/aQC+r9v5gAWNi6z+8gBsgcDq3L8qABsBK9RfCYDNDazM/CsDsBmBlU1/dQC+z9tqYN7Rv6L+ygBsbmBF5l8LgM0IrGj66wGwGYHVTH9NADYjsJbprw3AthxYevBvDMB2dWxe1l9bRn0AtlBg2c7fHIDaD2wIzEH+s4mGRgBsCCxdfmMANkewXOMPBMCGwJLlBwFgywssad1vB4DNDCxx8oMCUCOwBYTuAr8rmGxwAGwMLE99aABaBrZ4wJ7fB1bfAgCbIVjK1LcIAGFgswTQM/9qRylLALxMwYaBqfR2Jr4bAJ4Y1BxcTqcNBXnZT7Xwl7Nd6dvxf55iHqHKkFIUAAAAAElFTkSuQmCC"


ICON_BADGE_B64 = "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"


def send_text(message):
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    return requests.post(TELEGRAM_SEND_MSG_URL, json=payload, timeout=15)


def send_photo_from_url(photo_url, caption):
    img = requests.get(photo_url, timeout=25)
    files = {"photo": ("setup.png", img.content)}
    data = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"}
    return requests.post(TELEGRAM_SEND_PHOTO_URL, data=data, files=files, timeout=25)


def gh_headers():
    return {"Authorization": "token " + GITHUB_TOKEN, "Accept": "application/vnd.github+json"}


def gh_load_history():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return [], None
    url = "https://api.github.com/repos/" + GITHUB_REPO + "/contents/" + HISTORY_PATH
    r = requests.get(url, headers=gh_headers(), timeout=15)
    if r.status_code == 200:
        j = r.json()
        content = base64.b64decode(j["content"]).decode("utf-8")
        try:
            data = json.loads(content)
        except Exception:
            data = []
        return data, j["sha"]
    return [], None


def gh_save_history(history_list, sha):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
    url = "https://api.github.com/repos/" + GITHUB_REPO + "/contents/" + HISTORY_PATH
    content_str = json.dumps(history_list, indent=2)
    content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
    body = {"message": "Update signal history", "content": content_b64, "branch": "main"}
    if sha:
        body["sha"] = sha
    r = requests.put(url, headers=gh_headers(), json=body, timeout=15)
    return r.status_code in (200, 201)


def gh_load_json(path):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return [], None
    url = "https://api.github.com/repos/" + GITHUB_REPO + "/contents/" + path
    r = requests.get(url, headers=gh_headers(), timeout=15)
    if r.status_code == 200:
        j = r.json()
        content = base64.b64decode(j["content"]).decode("utf-8")
        try:
            data = json.loads(content)
        except Exception:
            data = []
        return data, j["sha"]
    return [], None


def gh_save_json(path, data_list, sha):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
    url = "https://api.github.com/repos/" + GITHUB_REPO + "/contents/" + path
    content_str = json.dumps(data_list, indent=2)
    content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
    body = {"message": "Update " + path, "content": content_b64, "branch": "main"}
    if sha:
        body["sha"] = sha
    r = requests.put(url, headers=gh_headers(), json=body, timeout=15)
    return r.status_code in (200, 201)


def send_push_to_all(title, body_text, url_path="/"):
    subs, sha = gh_load_json(SUBS_PATH)
    if not subs or not VAPID_PRIVATE_KEY:
        return
    payload = json.dumps({"title": title, "body": body_text, "url": url_path})
    still_valid = []
    changed = False
    for sub in subs:
        if not _push_allowed(sub):
            still_valid.append(sub)
            continue
        try:
            webpush(
                subscription_info={k: v for k, v in sub.items() if k != "_k"},
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_CLAIMS_EMAIL},
                ttl=900,
                headers={"Urgency": "high"}
            )
            still_valid.append(sub)
        except WebPushException as e:
            status = e.response.status_code if e.response is not None else None
            if status in (404, 410):
                changed = True  # expired subscription, drop it
            else:
                still_valid.append(sub)
                print("Push send failed (kept):", e)
        except Exception as e:
            still_valid.append(sub)
            print("Push send error (kept):", e)
    if changed:
        gh_save_json(SUBS_PATH, still_valid, sha)


def fetch_closes(symbol="XAU/USD", interval="15min", outputsize=200):
    if not TWELVE_DATA_KEY:
        return None
    url = "https://api.twelvedata.com/time_series"
    params = {"symbol": symbol, "interval": interval, "outputsize": outputsize, "apikey": TWELVE_DATA_KEY, "format": "JSON"}
    try:
        r = requests.get(url, params=params, timeout=20)
        data = r.json()
    except Exception as e:
        print("Twelve Data request failed (fetch_closes):", e)
        return None
    if "values" not in data:
        print("Twelve Data error:", data)
        return None
    values = list(reversed(data["values"]))
    try:
        closes = [float(v["close"]) for v in values]
    except Exception as e:
        print("Failed parsing closes:", e)
        return None
    return closes


def fetch_ohlc(symbol="XAU/USD", interval="15min", outputsize=700):
    import time as _time
    if not TWELVE_DATA_KEY:
        return None
    url = "https://api.twelvedata.com/time_series"
    params = {"symbol": symbol, "interval": interval, "outputsize": outputsize, "apikey": TWELVE_DATA_KEY, "format": "JSON", "timezone": "UTC"}
    try:
        r = requests.get(url, params=params, timeout=25)
        data = r.json()
    except Exception as e:
        print("Twelve Data request failed:", e)
        return None
    if "values" not in data:
        print("Twelve Data error:", data)
        return None
    values = list(reversed(data["values"]))
    raw_bars = []
    for v in values:
        try:
            t = int(_time.mktime(_time.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S")))
            raw_bars.append({"time": t, "open": float(v["open"]), "high": float(v["high"]), "low": float(v["low"]), "close": float(v["close"])})
        except Exception:
            continue

    # Drop stale/placeholder bars from closed-market periods (e.g. weekends):
    # a real trading bar for gold almost always has some intrabar range.
    # Only strip RUNS of 3+ consecutive zero-range bars with the same close,
    # so genuine brief quiet moments in live trading are kept.
    bars = []
    i = 0
    n = len(raw_bars)
    while i < n:
        b = raw_bars[i]
        is_flat = b["open"] == b["high"] == b["low"] == b["close"]
        if is_flat:
            j = i
            while j < n and raw_bars[j]["open"] == raw_bars[j]["high"] == raw_bars[j]["low"] == raw_bars[j]["close"] == b["close"]:
                j += 1
            run_len = j - i
            if run_len >= 3:
                i = j
                continue
        bars.append(b)
        i += 1

    return bars


def build_chart_config(closes, entry, sl, tp1, tp2, tp3, signal):
    n = len(closes)
    labels = [str(i) for i in range(n)]
    flat_entry = [entry] * n
    flat_sl = [sl] * n
    flat_tp1 = [tp1] * n
    flat_tp2 = [tp2] * n
    flat_tp3 = [tp3] * n

    return {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [
                {"label": "Price", "data": closes, "borderColor": "#d1d4dc", "borderWidth": 1.5, "pointRadius": 0, "fill": False},
                {"label": "Entry", "data": flat_entry, "borderColor": "#2962ff", "borderWidth": 1, "borderDash": [6, 4], "pointRadius": 0, "fill": False},
                {"label": "SL", "data": flat_sl, "borderColor": "#ef5350", "borderWidth": 1, "borderDash": [6, 4], "pointRadius": 0, "fill": False},
                {"label": "TP1", "data": flat_tp1, "borderColor": "#26a69a", "borderWidth": 1, "borderDash": [3, 3], "pointRadius": 0, "fill": False},
                {"label": "TP2", "data": flat_tp2, "borderColor": "#26a69a", "borderWidth": 1, "borderDash": [3, 3], "pointRadius": 0, "fill": False},
                {"label": "TP3", "data": flat_tp3, "borderColor": "#26a69a", "borderWidth": 1, "borderDash": [3, 3], "pointRadius": 0, "fill": False}
            ]
        },
        "options": {
            "title": {"display": True, "text": "XAUUSD - " + signal + " SETUP", "fontColor": "#ffffff"},
            "legend": {"labels": {"fontColor": "#ffffff"}},
            "scales": {
                "xAxes": [{"ticks": {"fontColor": "#ffffff", "maxTicksLimit": 8}, "gridLines": {"color": "#2a2e39"}}],
                "yAxes": [{"ticks": {"fontColor": "#ffffff"}, "gridLines": {"color": "#2a2e39"}}]
            }
        }
    }


def render_chart_png_bytes(config):
    """POST to QuickChart instead of a giant GET URL - avoids the ~19,000+ character
    URL that a 200-point, 6-line chart produces, which was silently rejected before."""
    body = {"chart": config, "width": 900, "height": 500, "backgroundColor": "#131722",
             "devicePixelRatio": 2, "format": "png"}
    r = requests.post("https://quickchart.io/chart", json=body, timeout=25)
    r.raise_for_status()
    return r.content


def send_photo_bytes(photo_bytes, caption):
    files = {"photo": ("setup.png", photo_bytes)}
    data = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"}
    return requests.post(TELEGRAM_SEND_PHOTO_URL, data=data, files=files, timeout=25)


def build_caption(symbol, signal, kind, entry, sl, tp1, tp2, tp3):
    dot = "🟢" if signal == "BUY" else "🔴"
    title = (signal + " SETUP") if kind == "signal" else (signal + " ZONE TOUCHED AGAIN")
    caption = dot + " <b>" + symbol + " / GOLD</b>\n\n<b>" + title + "</b>\n\nEntry: " + entry + "\nSL: " + sl + "\n\nTP1: " + tp1 + "\nTP2: " + tp2 + "\nTP3: " + tp3
    return caption


def compute_outcome_and_excursion(sig, bars):
    # Returns {"outcome": "SL"/"TP"/"OPEN", "mfe_r": float, "mae_r": float} or None.
    # mfe_r = best price move in the trade's favor before exit, in R-multiples (risk units).
    # mae_r = worst price move against the trade before exit, in R-multiples.
    # Walks candles chronologically from the signal's own timestamp; if a bar's range
    # touches both SL and TP1, SL is assumed first (conservative, matches prior behavior).
    if "time_unix" not in sig:
        return None
    try:
        entry_t = int(sig["time_unix"])
        entry_v = float(sig["entry"])
        sl_v = float(sig["sl"])
        tp1_v = float(sig["tp1"])
        direction = sig["signal"]
        risk = abs(entry_v - sl_v)
        if risk == 0:
            return None
    except Exception:
        return None

    relevant = [b for b in bars if b["time"] >= entry_t]
    outcome = "OPEN"
    mfe_r = 0.0
    mae_r = 0.0
    for b in relevant:
        if direction == "BUY":
            favorable = (b["high"] - entry_v) / risk
            adverse = (entry_v - b["low"]) / risk
            hit_sl = b["low"] <= sl_v
            hit_tp = b["high"] >= tp1_v
        else:
            favorable = (entry_v - b["low"]) / risk
            adverse = (b["high"] - entry_v) / risk
            hit_sl = b["high"] >= sl_v
            hit_tp = b["low"] <= tp1_v
        mfe_r = max(mfe_r, favorable)
        mae_r = max(mae_r, adverse)
        if hit_sl:
            outcome = "SL"
            break
        if hit_tp:
            outcome = "TP"
            break

    return {"outcome": outcome, "mfe_r": round(mfe_r, 2), "mae_r": round(mae_r, 2)}


_stats_cache = {"data": None, "ts": 0}
STATS_CACHE_TTL = 300  # seconds


def get_7day_stats():
    import time as _time
    now = _time.time()
    if _stats_cache["data"] is not None and (now - _stats_cache["ts"]) < STATS_CACHE_TTL:
        return _stats_cache["data"]

    history, _ = gh_load_history()
    cutoff = now - 7 * 24 * 3600
    week_signals = [s for s in history if s.get("kind") == "signal" and s.get("time_unix", 0) >= cutoff]

    result = {"total": len(week_signals), "sl_hit": 0, "tp_hit": 0, "open": 0, "untracked": 0}
    mfe_values, mae_values, mfe_on_losses = [], [], []

    if week_signals and TWELVE_DATA_KEY:
        bars = fetch_ohlc(outputsize=700)
        if not bars:
            # Full 7-day window failed - likely a Twelve Data quota/credit ceiling tied
            # to request size (Market Context's smaller 300-bar request keeps working).
            # Fall back to a smaller, cheaper request rather than showing nothing.
            print("7-day stats: 700-bar fetch failed, falling back to 300-bar request")
            bars = fetch_ohlc(outputsize=300)
        if bars:
            for s in week_signals:
                r = compute_outcome_and_excursion(s, bars)
                if r is None:
                    result["untracked"] += 1
                    continue
                outcome = r["outcome"]
                mfe_values.append(r["mfe_r"])
                mae_values.append(r["mae_r"])
                if outcome == "SL":
                    result["sl_hit"] += 1
                    mfe_on_losses.append(r["mfe_r"])
                elif outcome == "TP":
                    result["tp_hit"] += 1
                elif outcome == "OPEN":
                    result["open"] += 1
        else:
            result["untracked"] = len(week_signals)
    else:
        result["untracked"] = len(week_signals)

    resolved = result["sl_hit"] + result["tp_hit"]
    result["win_rate"] = round(100.0 * result["tp_hit"] / resolved, 1) if resolved > 0 else None
    result["avg_mfe_r"] = round(sum(mfe_values) / len(mfe_values), 2) if mfe_values else None
    result["avg_mae_r"] = round(sum(mae_values) / len(mae_values), 2) if mae_values else None
    result["avg_mfe_r_on_losses"] = round(sum(mfe_on_losses) / len(mfe_on_losses), 2) if mfe_on_losses else None

    _stats_cache["data"] = result
    _stats_cache["ts"] = now
    return result


@app.route("/", methods=["GET"])
def home():
    html = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Bullion Radar</title>
<link rel="manifest" href="/manifest.json">
<link rel="icon" href="/icon192.png">
<link rel="apple-touch-icon" href="/icon192.png">
<meta name="theme-color" content="#0d1117">
<style>
:root {
  --bg: #0d1117; --card: #161b22; --card2: #1c2129; --border: #262c36;
  --text: #e6edf3; --muted: #8b949e; --accent: #d4af37;
  --buy: #3fb950; --buy-bg: rgba(63,185,80,0.12);
  --sell: #f85149; --sell-bg: rgba(248,81,73,0.12);
  --shadow: 0 8px 24px rgba(0,0,0,0.35);
}
html[data-theme="light"] {
  --bg: #f4f6f8; --card: #ffffff; --card2: #f0f2f5; --border: #e2e6ea;
  --text: #16181d; --muted: #6a7280; --accent: #b8860b;
  --buy: #1a7f37; --buy-bg: rgba(26,127,55,0.10);
  --sell: #cf222e; --sell-bg: rgba(207,34,46,0.10);
  --shadow: 0 8px 24px rgba(0,0,0,0.08);
}
* { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
body {
  margin:0; background:var(--bg); color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
  padding-bottom:50px; transition: background 0.35s ease, color 0.35s ease;
}
.header {
  padding:16px 18px; background:var(--card); border-bottom:1px solid var(--border);
  position:sticky; top:0; z-index:10; display:flex; justify-content:space-between; align-items:center;
  backdrop-filter: blur(10px); transition: background 0.35s ease, border-color 0.35s ease;
}
.brand { display:flex; align-items:center; gap:8px; }
.brand .logo {
  width:28px; height:28px; border-radius:50%; background:linear-gradient(135deg,#f2c94c,#b8860b);
  display:flex; align-items:center; justify-content:center; font-weight:800; color:#161b22; font-size:13px;
}
.brand h1 { font-size:14px; margin:0; font-weight:700; letter-spacing:0.2px; }
.brand .sub { font-size:11px; color:var(--muted); margin-top:1px; }
.header-actions { display:flex; align-items:center; gap:6px; }
.theme-toggle {
  width:36px; height:21px; border-radius:20px; background:var(--card2); border:1px solid var(--border);
  position:relative; cursor:pointer; transition:background 0.3s;
}
.theme-toggle .knob {
  position:absolute; top:2px; left:2px; width:15px; height:15px; border-radius:50%;
  background:var(--accent); transition: transform 0.3s ease; display:flex; align-items:center; justify-content:center; font-size:9px;
}
html[data-theme="light"] .theme-toggle .knob { transform: translateX(15px); }
.switch-btn {
  background:var(--card2); border:1px solid var(--border); border-radius:9px; width:29px; height:29px;
  font-size:13px; cursor:pointer; display:flex; align-items:center; justify-content:center;
}
.ticker-strip {
  overflow:hidden; background:var(--card2); border-bottom:1px solid var(--border);
  white-space:nowrap; position:relative; padding:8px 0;
}
.ticker-track {
  display:inline-flex; align-items:center; animation: ticker-scroll 55s linear infinite;
}
.ticker-strip:hover .ticker-track { animation-play-state: paused; }
@keyframes ticker-scroll {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}
.ticker-item {
  display:inline-flex; align-items:center; gap:6px; padding:0 18px; font-size:13px; flex-shrink:0;
}
.ticker-item .tsym { font-weight:800; color:#39ff14; text-shadow: 0 0 6px rgba(57,255,20,0.95), 0 0 14px rgba(57,255,20,0.6); }
.ticker-item .tprice { color:#39ff14; text-shadow: 0 0 5px rgba(57,255,20,0.8); font-weight:600; }
.ticker-strip.forex .ticker-item .tsym { color:#ffcc00; text-shadow: 0 0 6px rgba(255,204,0,0.95), 0 0 14px rgba(255,204,0,0.6); }
.ticker-strip.forex .ticker-item .tprice { color:#ffcc00; text-shadow: 0 0 5px rgba(255,204,0,0.8); }
.ticker-item .tchange.up { color:#26a69a; font-weight:600; }
.ticker-item .tchange.down { color:#ef5350; font-weight:600; }
.ticker-item .tgainer-tag {
  font-size:10px; background:#f4c43022; color:#f4c430; border-radius:5px; padding:1px 5px; font-weight:700;
}
.ticker-loading { padding:0 18px; font-size:13px; color:var(--text-dim); }
.chooser-overlay {
  display:none; position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:100;
  align-items:center; justify-content:center; padding:20px;
}
.chooser-overlay.show { display:flex; }
.chooser-box {
  background:var(--card); border:1px solid var(--border); border-radius:18px; padding:24px;
  max-width:400px; width:100%; box-shadow: var(--shadow);
}
.chooser-box h2 { margin:0 0 6px; font-size:19px; }
.chooser-box p { margin:0 0 18px; color:var(--muted); font-size:13px; }
.chooser-option {
  display:flex; gap:14px; align-items:center; padding:14px; border-radius:14px; background:var(--card2);
  border:1px solid var(--border); margin-bottom:10px; cursor:pointer; transition: transform 0.15s, border-color 0.2s;
}
.chooser-option:active { transform: scale(0.97); }
.chooser-option:hover { border-color: var(--accent); }
.chooser-icon { font-size:26px; }
.chooser-title { font-weight:700; font-size:14px; margin-bottom:3px; }
.chooser-desc { font-size:12px; color:var(--muted); line-height:1.4; }
.setups-hint { font-size:11px; color:var(--muted); text-align:center; padding:8px 16px 12px; }
.setups-tooltip {
  position:absolute; background:var(--card2); border:1px solid var(--accent); border-radius:10px;
  padding:10px 12px; font-size:12px; box-shadow: var(--shadow); z-index:5; pointer-events:none;
  min-width:150px;
}
.setups-tooltip .t-row { display:flex; justify-content:space-between; gap:10px; padding:2px 0; }
.setups-tooltip .t-label { color:var(--muted); }
.setups-tooltip .t-title { font-weight:700; margin-bottom:4px; }
.refresh-btn:active { transform: scale(0.94); }
.refresh-btn.spinning svg { animation: spin 0.8s linear infinite; }
@keyframes spin { from{transform:rotate(0deg);} to{transform:rotate(360deg);} }

.stats-strip { display:flex; gap:10px; padding:14px 16px 4px; overflow-x:auto; }
.week-panel {
  margin:14px 16px 0; background:var(--card); border:1px solid var(--border); border-radius:16px;
  padding:16px; box-shadow: var(--shadow);
}
.week-panel h2 { font-size:14px; margin:0 0 12px; font-weight:700; display:flex; align-items:center; gap:6px; }
.week-grid { display:grid; grid-template-columns: repeat(4, 1fr); gap:8px; }
.week-cell { text-align:center; padding:10px 4px; border-radius:10px; background:var(--card2); }
.week-cell .num { font-size:19px; font-weight:800; }
.week-cell .lbl { font-size:10.5px; color:var(--muted); margin-top:3px; }
.week-cell.sl .num { color:var(--sell); }
.week-cell.tp .num { color:var(--buy); }
.week-note { font-size:11px; color:var(--muted); margin-top:10px; text-align:center; line-height:1.6; }
.stat-pill {
  background:var(--card); border:1px solid var(--border); border-radius:12px; padding:10px 16px;
  min-width:84px; text-align:center; flex-shrink:0; box-shadow: var(--shadow);
}
.stat-pill .num { font-size:20px; font-weight:800; }
.stat-pill .lbl { font-size:11px; color:var(--muted); margin-top:2px; }
.stat-pill.buy .num { color:var(--buy); }
.stat-pill.sell .num { color:var(--sell); }

.filters { display:flex; gap:8px; padding:14px 16px 4px; overflow-x:auto; }
.chip {
  padding:7px 14px; border-radius:20px; border:1px solid var(--border); background:var(--card);
  color:var(--muted); font-size:13px; font-weight:600; cursor:pointer; flex-shrink:0; transition: all 0.2s;
}
.chip.active { background:var(--accent); color:#161b22; border-color:var(--accent); }

.chart-embed-card {
  margin:14px 16px 4px; background:var(--card); border:1px solid var(--border); border-radius:16px;
  overflow:hidden; box-shadow: var(--shadow);
}
.chart-embed-header { padding:12px 16px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border); }
.chart-embed-header h2 { font-size:14px; margin:0; font-weight:700; }
.chart-embed-header .live-dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--buy); margin-right:6px; animation: pulse 1.5s infinite; }
.symbol-select {
  background:var(--card2); color:var(--text); border:1px solid var(--border); border-radius:8px;
  padding:5px 8px; font-size:12px; font-weight:600; cursor:pointer;
}
@keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.3;} }
#tvChartContainer { height:340px; }
.card-link { text-decoration:none; color:inherit; display:block; }
.tap-hint { font-size:10.5px; color:var(--muted); padding:0 16px 12px; display:flex; align-items:center; gap:4px; }
.card { margin:14px 16px; background:var(--card); border:1px solid var(--border); border-radius:16px;
  overflow:hidden; box-shadow: var(--shadow); opacity:0; transform:translateY(10px);
  animation: cardIn 0.4s ease forwards; transition: transform 0.15s; }
.card:active { transform: scale(0.98); }
@keyframes cardIn { to { opacity:1; transform:translateY(0); } }
.card img { width:100%; display:block; background:var(--card2); }
.card-body { padding:16px; }
.badge-row { display:flex; justify-content:space-between; align-items:center; }
.badge { display:inline-flex; align-items:center; gap:5px; padding:5px 13px; border-radius:20px; font-weight:800; font-size:13px; letter-spacing:0.3px; }
.badge.buy { background:var(--buy-bg); color:var(--buy); }
.badge.sell { background:var(--sell-bg); color:var(--sell); }
.kind-tag { font-size:11px; padding:4px 10px; border-radius:8px; background:var(--card2); color:var(--muted); font-weight:600; }
.rows { margin-top:14px; }
.row { display:flex; justify-content:space-between; padding:9px 0; border-bottom:1px solid var(--border); font-size:15px; }
.row:last-child { border-bottom:none; }
.row .label { color:var(--muted); font-size:13px; }
.row .value { font-weight:700; font-variant-numeric: tabular-nums; }
.entry .value { color:#58a6ff; }
.sl .value { color:var(--sell); }
.tp .value { color:var(--buy); }
.time { color:var(--muted); font-size:11.5px; padding:0 16px 14px; }
.empty { text-align:center; color:var(--muted); padding:80px 24px; }
.empty .emoji { font-size:42px; margin-bottom:14px; }
.section-title { padding:10px 16px 0; color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:0.6px; font-weight:700; }
.ind-upd { font-size:11px; color:var(--muted); }
.ind-tf { display:flex; gap:6px; padding:8px 14px 0; }
.ind-tf button { background:var(--card2); color:var(--muted); border:1px solid var(--border); border-radius:8px; padding:5px 12px; font-size:12px; font-weight:700; cursor:pointer; }
.ind-tf button.active { background:var(--accent); color:#111; border-color:var(--accent); }
.ind-legend { display:flex; flex-wrap:wrap; gap:10px 14px; padding:8px 14px 0; font-size:11px; color:var(--muted); }
.ind-legend i { display:inline-block; width:14px; height:0; border-top:2px solid; vertical-align:middle; margin-right:5px; }
.ind-info { padding:10px 14px 14px; font-size:13px; }
.ind-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; gap:8px; flex-wrap:wrap; }
.ind-chip { padding:3px 10px; border-radius:20px; font-weight:700; font-size:12px; }
.ind-chip.buy { background:var(--buy-bg); color:var(--buy); }
.ind-chip.sell { background:var(--sell-bg); color:var(--sell); }
.ind-chip.neutral { background:var(--card2); color:var(--muted); }
.ind-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:6px; }
.ind-cell { background:var(--card2); border-radius:8px; padding:6px 4px; text-align:center; }
.ind-cell .v { font-weight:700; font-size:12px; }
.ind-cell .l { font-size:10px; color:var(--muted); margin-top:2px; }
body { padding-bottom: 86px; }
.tabpane { display:none; }
.tabpane.active { display:block; }
.price-pill { display:flex; align-items:center; gap:6px; background:var(--card2); border:1px solid var(--border); border-radius:20px; padding:5px 11px; font-size:13px; font-weight:800; font-variant-numeric:tabular-nums; cursor:pointer; }
.price-pill .pp-dot { width:7px; height:7px; border-radius:50%; background:var(--buy); animation:pulse 1.5s infinite; }
.tabbar { position:fixed; left:0; right:0; bottom:0; z-index:30; display:flex; background:var(--card); border-top:1px solid var(--border); padding:6px 6px calc(6px + env(safe-area-inset-bottom)); box-shadow:0 -6px 20px rgba(0,0,0,0.25); }
.tabbar button { flex:1; background:none; border:0; color:var(--muted); font-size:11px; font-weight:700; display:flex; flex-direction:column; align-items:center; gap:3px; padding:6px 0; border-radius:12px; cursor:pointer; }
.tabbar button .ti { font-size:19px; filter:grayscale(1); opacity:0.7; }
.tabbar button.active { color:var(--accent); background:var(--card2); }
.tabbar button.active .ti { filter:none; opacity:1; }
.seg { display:flex; margin:14px 16px 0; background:var(--card2); border:1px solid var(--border); border-radius:12px; padding:3px; gap:3px; }
.seg button { flex:1; background:none; border:0; color:var(--muted); font-size:12px; font-weight:700; padding:8px 4px; border-radius:9px; cursor:pointer; }
.seg button.active { background:var(--accent); color:#161b22; }
.sess-strip { display:grid; grid-template-columns:repeat(4,1fr); gap:6px; margin:14px 16px 0; }
.sess-pill { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:8px 4px; text-align:center; }
.sess-pill .sn { font-size:11px; font-weight:800; }
.sess-pill .ss { font-size:10px; color:var(--muted); margin-top:3px; }
.sess-pill.open { border-color:var(--buy); background:var(--buy-bg); }
.sess-pill.open .sn::before { content:"● "; color:var(--buy); }
.sess-note { margin:8px 16px 0; font-size:12px; color:var(--muted); text-align:center; }
.news-banner { margin:14px 16px 0; padding:10px 14px; border-radius:12px; font-size:13px; font-weight:600; background:rgba(244,196,48,0.12); border:1px solid #f4c430; color:var(--text); }
.news-banner.hot { background:var(--sell-bg); border-color:var(--sell); }
.panel { margin:14px 16px 0; background:var(--card); border:1px solid var(--border); border-radius:16px; padding:14px 16px; box-shadow:var(--shadow); }
.panel h3 { margin:0 0 10px; font-size:14px; font-weight:800; }
.panel .small, .small { font-size:11.5px; color:var(--muted); line-height:1.6; }
.sec-head { display:flex; justify-content:space-between; align-items:center; padding:16px 18px 0; }
.sec-head h2 { margin:0; font-size:18px; }
.chips-row { display:flex; gap:8px; padding:12px 16px 0; overflow-x:auto; }
.hero { margin:14px 16px 0; padding:18px 16px; border-radius:16px; border:1px solid var(--border); background:linear-gradient(135deg,var(--card),var(--card2)); text-align:center; box-shadow:var(--shadow); }
.hero .hn { font-size:38px; font-weight:900; font-variant-numeric:tabular-nums; }
.hero .hl { font-size:12px; color:var(--muted); margin-top:2px; }
.hero .hs { font-size:12px; margin-top:10px; color:var(--muted); }
.pos { color:var(--buy); } .neg { color:var(--sell); } .neu { color:var(--muted); }
.kgrid { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin:12px 16px 0; }
.kcell { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:10px 2px; text-align:center; }
.kcell .kv { font-size:19px; font-weight:800; }
.kcell .kl { font-size:10px; color:var(--muted); margin-top:3px; padding:0 2px; }
.drow { display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid var(--border); font-size:13px; }
.drow:last-child { border-bottom:0; }
.drow span:first-child { color:var(--muted); }
.drow b { font-variant-numeric:tabular-nums; }
.logrow { display:flex; justify-content:space-between; align-items:center; gap:8px; padding:10px 0; border-bottom:1px solid var(--border); }
.logrow:last-child { border-bottom:0; }
.logrow .lt { font-size:11px; color:var(--muted); margin-top:3px; }
.rchip { display:inline-block; padding:3px 9px; border-radius:8px; font-size:11px; font-weight:800; }
.rchip.win { background:var(--buy-bg); color:var(--buy); }
.rchip.loss { background:var(--sell-bg); color:var(--sell); }
.rchip.open { background:rgba(212,175,55,0.15); color:var(--accent); }
.rchip.mixed { background:var(--card2); color:var(--muted); }
.fld { display:flex; justify-content:space-between; align-items:center; gap:10px; margin-bottom:8px; font-size:13px; }
.fld label { color:var(--muted); }
.fld input { width:120px; background:var(--card2); color:var(--text); border:1px solid var(--border); border-radius:8px; padding:8px; font-size:14px; text-align:right; }
.btn { width:100%; background:var(--accent); color:#161b22; border:0; border-radius:10px; padding:10px; font-weight:800; font-size:13px; cursor:pointer; margin:4px 0 10px; }
.btn.alt { background:var(--card2); color:var(--text); border:1px solid var(--border); }
.cout { background:var(--card2); border-radius:12px; padding:10px 12px; font-size:13px; }
.plan-bar { position:relative; height:10px; border-radius:6px; margin:16px 0 22px; background:linear-gradient(90deg,var(--sell-bg),var(--card2) 33%,var(--buy-bg)); border:1px solid var(--border); }
.plan-bar .tick { position:absolute; top:-3px; width:2px; height:14px; background:var(--muted); }
.plan-bar .tl { position:absolute; top:14px; font-size:9px; color:var(--muted); transform:translateX(-50%); white-space:nowrap; }
.plan-bar .you { position:absolute; top:-5px; width:6px; height:18px; border-radius:3px; background:var(--accent); transform:translateX(-50%); box-shadow:0 0 8px var(--accent); }
.cal-item { display:flex; justify-content:space-between; gap:10px; padding:9px 0; border-bottom:1px solid var(--border); font-size:13px; }
.cal-item:last-child { border-bottom:0; }
.cal-item .cs { font-size:11px; color:var(--muted); margin-top:2px; }
.cal-item .cc { font-size:12px; font-weight:800; white-space:nowrap; text-align:right; }
.tips li { margin-bottom:7px; }
.linkrow { display:block; padding:11px 0; border-bottom:1px solid var(--border); color:var(--text); text-decoration:none; font-size:14px; font-weight:600; }
.linkrow:last-child { border-bottom:0; }
</style>
<script>
(function(){
  var _f=window.fetch;
  window.fetch=function(){
    var a=arguments;
    return _f.apply(this,a).then(function(r){
      if(r.status===401){
        var u=String((a[0]&&a[0].url)||a[0]||"");
        if(u.indexOf("/auth")<0&&u.indexOf("/admin")<0&&window.__showLock) window.__showLock();
      }
      return r;
    });
  };
})();
</script>
</head>
<body>
<div id="lockOv" style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;z-index:99999;background:#0e0f12;color:#f2f3f5;align-items:center;justify-content:center;padding:24px;font-family:system-ui,sans-serif">
  <div style="max-width:340px;width:100%;text-align:center">
    <img src="/icon192.png" alt="" style="width:84px;height:84px;border-radius:18px;margin:0 auto 14px;display:block">
    <h2 style="margin:0 0 6px">Bullion Radar</h2>
    <p style="color:#9aa0ab;margin:0 0 16px">Private access. Enter your access key to continue.</p>
    <input id="lockKey" placeholder="GS-XXXX-XXXX-XXXX" autocapitalize="characters" autocomplete="off" style="width:100%;box-sizing:border-box;background:#181a20;color:#f2f3f5;border:1px solid #2a2d36;border-radius:10px;padding:13px;font-size:16px;text-align:center;letter-spacing:1px">
    <button id="lockBtn" style="width:100%;margin-top:10px;background:#f5b301;color:#111;border:0;border-radius:10px;padding:13px;font-size:16px;font-weight:700">Unlock</button>
    <div id="lockErr" style="color:#ff8a8f;font-size:13px;margin-top:10px;min-height:18px"></div>
  </div>
</div>
<script>
window.__showLock=function(){var o=document.getElementById("lockOv");if(o)o.style.display="flex";};
document.getElementById("lockBtn").onclick=async function(){
  var k=document.getElementById("lockKey").value, e=document.getElementById("lockErr");
  e.textContent="Checking...";
  try{
    var r=await fetch("/auth",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({key:k})});
    var j=await r.json();
    if(r.ok){location.reload();}else{e.textContent=j.error||"Invalid key";}
  }catch(x){e.textContent="Network error, try again";}
};
document.getElementById("lockKey").addEventListener("keydown",function(ev){if(ev.key==="Enter")document.getElementById("lockBtn").click();});
fetch("/auth-status",{cache:"no-store"}).then(function(r){return r.json();}).then(function(s){if(s.gated&&!s.ok)window.__showLock();}).catch(function(){});
</script>
<div class="header">
  <div class="brand">
    <img class="logo" src="/icon192.png" alt="" style="background:none;border-radius:7px;object-fit:cover">
    <div>
      <h1>Bullion Radar</h1>
      <div class="sub">XAUUSD · Gold</div>
    </div>
  </div>
  <div class="header-actions">
    <div class="price-pill" id="pricePill" onclick="showTab('chart')"><span class="pp-dot"></span><span id="ppPrice">---</span></div>
    <div class="theme-toggle" id="themeToggle" onclick="toggleTheme()"><div class="knob" id="themeKnob">🌙</div></div>
    <button class="switch-btn" id="settingsBtn" onclick="openSettings()">⚙️</button>
    <button id="notifyBtn" style="display:none"></button>
  </div>
</div>

<div class="ticker-strip" id="tickerStrip">
  <div class="ticker-track" id="tickerTrack">
    <span class="ticker-loading">Loading market data…</span>
  </div>
</div>

<div class="ticker-strip forex" id="forexTickerStrip">
  <div class="ticker-track" id="forexTickerTrack">
    <span class="ticker-loading">Loading forex data…</span>
  </div>
</div>

<div class="chooser-overlay" id="chooserOverlay">
  <div class="chooser-box">
    <h2>Choose Your Chart</h2>
    <p>Pick which chart view you'd like to see</p>
    <div class="chooser-option" onclick="selectChart('ind')">
      <div class="chooser-icon">🥇</div>
      <div>
        <div class="chooser-title">Gold Indicator Chart</div>
        <div class="chooser-desc">XAUUSD 15M with your indicator: structure, BUY/SELL signals, Entry / SL / TP levels</div>
      </div>
    </div>
    <div class="chooser-option" onclick="selectChart('tv')">
      <div class="chooser-icon">📊</div>
      <div>
        <div class="chooser-title">Live TradingView Chart</div>
        <div class="chooser-desc">Full-featured live chart with indicators and drawing tools</div>
      </div>
    </div>
    <div class="chooser-option" onclick="selectChart('setups')">
      <div class="chooser-icon">📈</div>
      <div>
        <div class="chooser-title">My Setups Chart</div>
        <div class="chooser-desc">Candles with every past BUY/SELL setup marked - tap a marker for details</div>
      </div>
    </div>
  </div>
</div>

<div class="chooser-overlay" id="settingsOverlay">
  <div class="chooser-box">
    <h2>Settings</h2>
    <p>Notification preferences</p>
    <div class="chooser-option" onclick="return false;" style="cursor:default;">
      <div class="chooser-icon" id="settingsPushIcon">🔕</div>
      <div>
        <div class="chooser-title" id="settingsPushStatus">Notifications off</div>
        <div class="chooser-desc" id="settingsPushDesc">Tap below to enable phone alerts for new setups</div>
      </div>
    </div>
    <div class="chooser-option" onclick="enablePush()">
      <div class="chooser-icon">🔔</div>
      <div>
        <div class="chooser-title">Enable Notifications</div>
        <div class="chooser-desc">Get alerted even when your phone is locked</div>
      </div>
    </div>
    <div class="chooser-option" onclick="toggleSound()">
      <div class="chooser-icon" id="settingsSoundIcon">🔊</div>
      <div>
        <div class="chooser-title" id="settingsSoundTitle">Sound: On</div>
        <div class="chooser-desc">Play a sound when a new setup card appears in-app</div>
      </div>
    </div>
    <div class="chooser-option" onclick="closeSettings()" style="justify-content:center;">
      <div class="chooser-title">Close</div>
    </div>
  </div>
</div>

<div class="tabpane active" id="pane-chart">
<div id="newsBanner" class="news-banner" style="display:none"></div>
<div class="sess-strip" id="sessStrip"></div>
<div class="sess-note" id="sessNote"></div>
<div class="seg" id="viewSeg">
  <button data-v="ind" onclick="selectChart('ind')">Gold Indicator</button>
  <button data-v="tv" onclick="selectChart('tv')">TradingView</button>
  <button data-v="setups" onclick="selectChart('setups')">Setups</button>
</div>
<div class="chart-embed-card" id="tvCard">
  <div class="chart-embed-header">
    <h2><span class="live-dot"></span><span id="tvChartTitle">XAUUSD</span> Live Chart</h2>
    <select id="tvSymbolSelect" class="symbol-select" onchange="changeTVSymbol(this.value)">
      <option value="FOREXCOM:XAUUSD">XAUUSD (Gold)</option>
      <option value="FOREXCOM:EURUSD">EUR/USD</option>
      <option value="FOREXCOM:USDJPY">USD/JPY</option>
      <option value="FOREXCOM:GBPUSD">GBP/USD</option>
      <option value="FOREXCOM:USDCHF">USD/CHF</option>
      <option value="FOREXCOM:AUDUSD">AUD/USD</option>
      <option value="FOREXCOM:USDCAD">USD/CAD</option>
      <option value="FOREXCOM:NZDUSD">NZD/USD</option>
    </select>
  </div>
  <div id="tvChartContainer"></div>
</div>

<div class="chart-embed-card" id="setupsCard" style="display:none;">
  <div class="chart-embed-header">
    <h2><span class="live-dot"></span>My Setups Chart</h2>
  </div>
  <div id="setupsChartContainer" style="height:340px; position:relative;"></div>
  <div class="setups-hint">Tap near a marker to see its Entry / SL / TP details</div>
  <div id="setupsTooltip" class="setups-tooltip" style="display:none;"></div>
</div>

<div class="chart-embed-card" id="indCard" style="display:none;">
  <div class="chart-embed-header">
    <h2><span class="live-dot"></span>XAUUSD Gold Indicator</h2>
    <span class="ind-upd" id="indUpdated"></span>
  </div>
  <div class="ind-tf" id="indTFBar">
    <button data-tf="1" onclick="setIndTF('1')">1m</button>
    <button data-tf="5" onclick="setIndTF('5')">5m</button>
    <button data-tf="15" onclick="setIndTF('15')">15m</button>
    <button data-tf="60" onclick="setIndTF('60')">1H</button>
    <button data-tf="240" onclick="setIndTF('240')">4H</button>
  </div>
  <div id="indChartContainer" style="height:420px; position:relative;"></div>
  <div class="ind-legend">
    <span><i style="border-color:#ff9800"></i>Swing High</span>
    <span><i style="border-color:#42a5f5"></i>Swing Low</span>
    <span><i style="border-color:#2962ff"></i>Entry</span>
    <span><i style="border-color:#f85149"></i>SL</span>
    <span><i style="border-color:#3fb950"></i>TP1-3</span>
    <span><i style="border-color:#d4af37"></i>Zone re-touch</span>
  </div>
  <div class="ind-info" id="indInfo">Loading indicator...</div>
</div>

<div class="panel" id="ctxCard" style="margin-top:14px;">
  <h3>Key levels &amp; volatility</h3>
  <div class="kgrid" style="margin:0;" id="ctxGrid"><div class="small" style="grid-column:1/-1">Loading...</div></div>
  <div class="small" style="margin-top:8px">PDH/PDL = previous day high/low (UTC day). 1 pip = $0.10 on gold. ATR = average hourly range.</div>
</div>
</div>

<div class="tabpane" id="pane-results">
  <div class="sec-head"><h2>Performance</h2><span class="ind-upd" id="resUpdated"></span></div>
  <div class="chips-row" id="resPeriod">
    <div class="chip" data-p="1" onclick="setResPeriod('1')">Today</div>
    <div class="chip" data-p="7" onclick="setResPeriod('7')">7 Days</div>
    <div class="chip" data-p="30" onclick="setResPeriod('30')">30 Days</div>
    <div class="chip" data-p="0" onclick="setResPeriod('0')">All Time</div>
  </div>
  <div class="hero" id="resHero"><div class="small">Loading real results...</div></div>
  <div class="kgrid" id="resGrid"></div>
  <div class="panel"><h3>Equity curve (pips)</h3><div id="resCurve"></div></div>
  <div class="panel"><h3>Numbers</h3><div id="resRows"></div></div>
  <div class="panel"><h3>Trade log</h3><div id="resLog"></div></div>
  <div class="panel"><div class="small" id="resNote">
    <b>How this is counted:</b> only real BUY/SELL setups (zone re-touch alerts and test alerts are excluded). 1 pip = $0.10 on gold.
    Plan: one third of the position closes at each of TP1 (+1R), TP2 (+2R) and TP3 (+3R); whatever is left when price hits the original stop loss is a loss.
    If one candle touches both the stop and a target, the stop is counted first, so results are never flattered.
    Open trades are shown separately and are not in the totals.
  </div></div>
</div>

<div class="tabpane" id="pane-signals">
<div class="stats-strip" id="statsStrip"></div>
<div class="filters" id="filters"></div>
<div id="content"><div class="empty"><div class="emoji">⏳</div>Loading signals...</div></div>

</div>

<div class="tabpane" id="pane-tools">
  <div class="sec-head"><h2>Gold Toolkit</h2></div>
  <div class="panel">
    <h3>Position size calculator</h3>
    <div class="fld"><label>Account balance ($)</label><input id="cBal" type="number" inputmode="decimal" oninput="calcLots()"></div>
    <div class="fld"><label>Risk per trade (%)</label><input id="cRisk" type="number" inputmode="decimal" oninput="calcLots()"></div>
    <div class="fld"><label>Entry price</label><input id="cEntry" type="number" inputmode="decimal" oninput="calcLots()"></div>
    <div class="fld"><label>Stop loss price</label><input id="cSL" type="number" inputmode="decimal" oninput="calcLots()"></div>
    <button class="btn alt" onclick="fillFromSetup()">Use latest indicator setup</button>
    <div class="cout" id="cOut">Enter your numbers above.</div>
    <div class="small" style="margin-top:8px">Gold: 1 lot = 100 oz, so a $1 move = $100 per lot. Lot size = risk $ / (stop distance x 100).</div>
  </div>
  <div class="panel">
    <h3>Pips to dollars</h3>
    <div class="fld"><label>Pips</label><input id="pPips" type="number" inputmode="decimal" oninput="calcPips()"></div>
    <div class="fld"><label>Lot size</label><input id="pLots" type="number" inputmode="decimal" oninput="calcPips()"></div>
    <div class="cout" id="pOut">-</div>
  </div>
  <div class="panel">
    <h3>High-impact news</h3>
    <div class="chips-row" style="padding:0 0 10px;" id="calFilter">
      <div class="chip" data-f="USD" onclick="setCalFilter('USD')">USD only</div>
      <div class="chip" data-f="ALL" onclick="setCalFilter('ALL')">All currencies</div>
    </div>
    <div id="calList"><div class="small">Loading...</div></div>
    <div class="small" style="margin-top:8px">Gold reacts hardest to US data and Fed events. Spreads widen and stops get hunted: many traders stay flat 15 minutes before and after.</div>
  </div>
  <div class="panel">
    <h3>Gold trader's cheat sheet</h3>
    <ul class="tips small" style="padding-left:18px;margin:0;">
      <li>1 pip = $0.10 move. 10 pips = $1. Per 1.00 lot a pip is $10; per 0.01 lot it is $0.10.</li>
      <li>Best liquidity is the London and New York overlap, roughly 17:30 to 21:30 IST. Asia session is quieter and ranges more.</li>
      <li>Gold usually moves against the US dollar and against US real yields. A rising DXY or 10Y yield is a headwind.</li>
      <li>Biggest movers: NFP, CPI, FOMC and Fed speakers, PCE, GDP, plus geopolitical shocks.</li>
      <li>Risk 0.5% to 2% per trade. Size by stop distance, never by a fixed lot.</li>
      <li>This indicator scales out in thirds at 1R, 2R and 3R. Check the Results tab to see how it really performs.</li>
    </ul>
  </div>
  <div class="panel">
    <h3>More</h3>
    <a class="linkrow" href="/news">📰 Full economic calendar and news alerts</a>
    <a class="linkrow" href="/history">🕘 Notification history</a>
    <a class="linkrow" href="https://www.tradingview.com/chart/?symbol=FOREXCOM:XAUUSD" target="_blank" rel="noopener">📈 Open XAUUSD in TradingView</a>
  </div>
</div>

<nav class="tabbar" id="tabbar">
  <button data-tab="chart" onclick="showTab('chart')"><span class="ti">📈</span><span>Chart</span></button>
  <button data-tab="results" onclick="showTab('results')"><span class="ti">🏆</span><span>Results</span></button>
  <button data-tab="signals" onclick="showTab('signals')"><span class="ti">🔔</span><span>Signals</span></button>
  <button data-tab="tools" onclick="showTab('tools')"><span class="ti">🧰</span><span>Tools</span></button>
</nav>

<script>
let allSignals = [];
let currentFilter = "all";

function applyTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  document.getElementById("themeKnob").textContent = t === "light" ? "\u2600\ufe0f" : "\ud83c\udf19";
  localStorage.setItem("theme", t);
  if (typeof indApplyTheme === "function") indApplyTheme(t);
  const choice = localStorage.getItem("chartChoice");
  if (choice === "tv" && tvScriptLoaded !== undefined) {
    if (document.getElementById("tvCard").style.display !== "none") initTVWidget(t);
  } else if (choice === "setups" && window._lwChart) {
    const isLight = t === "light";
    window._lwChart.applyOptions({
      layout: { background: { color: isLight ? "#ffffff" : "#131722" }, textColor: isLight ? "#16181d" : "#d1d4dc" },
      grid: { vertLines: { color: isLight ? "#e2e6ea" : "#242832" }, horzLines: { color: isLight ? "#e2e6ea" : "#242832" } }
    });
  }
}
function toggleTheme() {
  const cur = document.documentElement.getAttribute("data-theme") || "dark";
  applyTheme(cur === "dark" ? "light" : "dark");
}

let tvScriptLoaded = false;
let currentTVSymbol = localStorage.getItem("tvSymbol") || "FOREXCOM:XAUUSD";

function changeTVSymbol(symbol) {
  currentTVSymbol = symbol;
  localStorage.setItem("tvSymbol", symbol);
  const label = symbol.replace("FOREXCOM:", "");
  document.getElementById("tvChartTitle").textContent = label === "XAUUSD" ? "XAUUSD" : label.slice(0,3) + "/" + label.slice(3);
  const theme = document.documentElement.getAttribute("data-theme") || "dark";
  initTVWidget(theme);
}

function initTVWidget(theme) {
  const container = document.getElementById("tvChartContainer");
  container.innerHTML = "";
  function draw() {
    new TradingView.widget({
      "autosize": true,
      "symbol": currentTVSymbol,
      "interval": "15",
      "timezone": "Etc/UTC",
      "theme": theme === "light" ? "light" : "dark",
      "style": "1",
      "locale": "en",
      "toolbar_bg": theme === "light" ? "#ffffff" : "#131722",
      "enable_publishing": false,
      "hide_top_toolbar": false,
      "hide_legend": false,
      "save_image": false,
      "container_id": "tvChartContainer"
    });
  }
  if (tvScriptLoaded) { draw(); return; }
  const s = document.createElement("script");
  s.src = "https://s3.tradingview.com/tv.js";
  s.onload = function() { tvScriptLoaded = true; draw(); };
  document.body.appendChild(s);
}

// ============= CHART CHOOSER =============
function openChooser() {
  document.getElementById("chooserOverlay").classList.add("show");
}
function closeChooser() {
  document.getElementById("chooserOverlay").classList.remove("show");
}

function openSettings() {
  document.getElementById("settingsOverlay").classList.add("show");
  refreshSettingsPanel();
}
function closeSettings() {
  document.getElementById("settingsOverlay").classList.remove("show");
}
function refreshSettingsPanel() {
  const icon = document.getElementById("settingsPushIcon");
  const status = document.getElementById("settingsPushStatus");
  const desc = document.getElementById("settingsPushDesc");
  if ("Notification" in window && Notification.permission === "granted") {
    icon.textContent = "🔔";
    status.textContent = "Notifications on";
    desc.textContent = "You'll be alerted even when your phone is locked";
  } else {
    icon.textContent = "🔕";
    status.textContent = "Notifications off";
    desc.textContent = "Tap below to enable phone alerts for new setups";
  }
  const soundOn = localStorage.getItem("soundEnabled") !== "off";
  document.getElementById("settingsSoundIcon").textContent = soundOn ? "🔊" : "🔇";
  document.getElementById("settingsSoundTitle").textContent = "Sound: " + (soundOn ? "On" : "Off");
}
function toggleSound() {
  const soundOn = localStorage.getItem("soundEnabled") !== "off";
  localStorage.setItem("soundEnabled", soundOn ? "off" : "on");
  refreshSettingsPanel();
}
let lwScriptLoaded = false;
let setupsChartBuilt = false;

// ============= APP SHELL: tabs, live price, sessions, news, results, tools =============
let livePrice = null;
function fmt2(v) { return Number(v).toFixed(2); }
function sgn(v, d) { const x = Number(v); return (x > 0 ? "+" : "") + x.toFixed(d === undefined ? 1 : d); }
function cls(v) { return v > 0 ? "pos" : (v < 0 ? "neg" : "neu"); }

function showTab(name) {
  document.querySelectorAll(".tabpane").forEach(function(p) { p.classList.toggle("active", p.id === "pane-" + name); });
  document.querySelectorAll("#tabbar button").forEach(function(b) { b.classList.toggle("active", b.getAttribute("data-tab") === name); });
  try { localStorage.setItem("tab", name); } catch (e) {}
  window.scrollTo(0, 0);
  if (name === "chart") { loadCtx(); loadCalendar(true); renderSessions(); }
  if (name === "results") loadResults();
  if (name === "signals") loadResults(false, true);
  if (name === "tools") { loadCalendar(); initCalc(); }
}
function paintViewSeg(which) {
  document.querySelectorAll("#viewSeg button").forEach(function(b) { b.classList.toggle("active", b.getAttribute("data-v") === which); });
}

// ---- live price (header pill) ----
async function pollPrice() {
  if (document.hidden) return;
  try {
    const d = await (await fetch("/live-price")).json();
    if (d && d.price) {
      livePrice = d.price;
      document.getElementById("ppPrice").textContent = fmt2(d.price);
      if (typeof renderPlan === "function") renderPlan();
    }
  } catch (e) {}
}
setInterval(pollPrice, 45000);
document.addEventListener("visibilitychange", function() { if (!document.hidden) pollPrice(); });

// ---- market sessions ----
const SESS = [
  { n: "Sydney", tz: "Australia/Sydney", o: 8, c: 17 },
  { n: "Tokyo", tz: "Asia/Tokyo", o: 9, c: 18 },
  { n: "London", tz: "Europe/London", o: 8, c: 17 },
  { n: "New York", tz: "America/New_York", o: 8, c: 17 }
];
const sessFmt = {};
function sessOpenAt(s, ms) {
  if (!sessFmt[s.tz]) sessFmt[s.tz] = new Intl.DateTimeFormat("en-US", { timeZone: s.tz, hour: "numeric", hour12: false, weekday: "short" });
  const parts = sessFmt[s.tz].formatToParts(new Date(ms));
  let h = 0, wd = "";
  parts.forEach(function(p) { if (p.type === "hour") h = parseInt(p.value, 10) % 24; if (p.type === "weekday") wd = p.value; });
  if (wd === "Sat" || wd === "Sun") return false;
  return h >= s.o && h < s.c;
}
function goldClosedAt(ms) {
  const d = new Date(ms), wd = d.getUTCDay(), h = d.getUTCHours();
  if (wd === 6) return true;
  if (wd === 5 && h >= 22) return true;
  if (wd === 0 && h < 22) return true;
  return false;
}
function dur(mins) {
  if (mins >= 1440) return Math.round(mins / 1440) + "d";
  const h = Math.floor(mins / 60), m = mins % 60;
  return h > 0 ? h + "h " + (m < 10 ? "0" : "") + m + "m" : m + "m";
}
function renderSessions() {
  const now = Date.now();
  const strip = document.getElementById("sessStrip");
  if (!strip) return;
  const openNow = [];
  strip.innerHTML = SESS.map(function(s) {
    const cur = sessOpenAt(s, now);
    let mins = 0;
    for (let k = 1; k <= 60 * 24 * 3; k += 5) {
      if (sessOpenAt(s, now + k * 60000) !== cur) { mins = k; break; }
    }
    if (cur) openNow.push(s.n);
    return '<div class="sess-pill ' + (cur ? "open" : "") + '"><div class="sn">' + s.n + '</div><div class="ss">' + (cur ? "closes " : "opens ") + dur(mins) + '</div></div>';
  }).join("");
  const note = document.getElementById("sessNote");
  if (goldClosedAt(now)) {
    note.innerHTML = "🔒 Gold market is closed for the weekend. Reopens Monday 03:30 IST.";
  } else if (openNow.indexOf("London") >= 0 && openNow.indexOf("New York") >= 0) {
    note.innerHTML = "🔥 London and New York overlap: highest liquidity and volatility.";
  } else if (openNow.length === 0) {
    note.textContent = "Quiet hours between sessions: expect thin liquidity.";
  } else {
    note.textContent = "Open now: " + openNow.join(", ");
  }
}
setInterval(renderSessions, 60000);

// ---- news calendar ----
let calEvents = [], calFilter = "USD", calLoadedAt = 0;
async function loadCalendar(bannerOnly) {
  try {
    if (Date.now() - calLoadedAt > 300000) {
      const d = await (await fetch("/forex-news")).json();
      calEvents = d.events || [];
      calLoadedAt = Date.now();
    }
  } catch (e) {}
  renderBanner();
  if (!bannerOnly) renderCalendar();
}
function renderBanner() {
  const el = document.getElementById("newsBanner");
  if (!el) return;
  const now = Date.now() / 1000;
  const ev = calEvents.filter(function(e) { return e.country === "USD" && e.impact === "High" && e.time_unix > now - 1200 && e.time_unix < now + 5400; })[0];
  if (!ev) { el.style.display = "none"; return; }
  const mins = Math.round((ev.time_unix - now) / 60);
  el.className = "news-banner" + (mins <= 15 ? " hot" : "");
  el.style.display = "";
  el.innerHTML = mins > 0
    ? "⚠️ <b>USD " + ev.title + "</b> in " + dur(mins) + ". Gold can spike: consider waiting before new entries."
    : "⚠️ <b>USD " + ev.title + "</b> was just released. Expect fast, whipsaw moves.";
}
function setCalFilter(f) { calFilter = f; renderCalendar(); }
function renderCalendar() {
  document.querySelectorAll("#calFilter .chip").forEach(function(c) { c.classList.toggle("active", c.getAttribute("data-f") === calFilter); });
  const el = document.getElementById("calList");
  if (!el) return;
  const now = Date.now() / 1000;
  const list = calEvents.filter(function(e) { return e.impact === "High" && e.time_unix > now - 1800 && (calFilter === "ALL" || e.country === "USD"); }).slice(0, 8);
  if (!list.length) { el.innerHTML = '<div class="small">No high-impact events coming up.</div>'; return; }
  el.innerHTML = list.map(function(e) {
    const mins = Math.round((e.time_unix - now) / 60);
    return '<div class="cal-item"><div><b>' + e.country + "</b> " + e.title + '<div class="cs">' + indFmtIST(e.time_unix) + ' IST · Fcst ' + (e.forecast || "-") + " · Prev " + (e.previous || "-") + '</div></div><div class="cc ' + (mins <= 60 ? "neg" : "neu") + '">' + (mins > 0 ? "in " + dur(mins) : "now") + "</div></div>";
  }).join("");
}

// ---- key levels & volatility ----
async function loadCtx() {
  try {
    const d = await (await fetch("/indicator-data?tf=240")).json();
    fillCtx(d.levels);
  } catch (e) {}
}
function fillCtx(L) {
  const g = document.getElementById("ctxGrid");
  if (!g || !L) return;
  const cell = function(v, l, c) { return '<div class="kcell"><div class="kv ' + (c || "") + '" style="font-size:15px">' + (v === undefined || v === null ? "-" : v) + '</div><div class="kl">' + l + "</div></div>"; };
  g.innerHTML =
    cell(L.pdh !== undefined ? fmt2(L.pdh) : null, "Prev day high") +
    cell(L.pdl !== undefined ? fmt2(L.pdl) : null, "Prev day low") +
    cell(L.day_open !== undefined ? fmt2(L.day_open) : null, "Day open") +
    cell(L.atr_pips !== undefined ? L.atr_pips + " pips" : null, "1H ATR") +
    cell(L.day_high !== undefined ? fmt2(L.day_high) : null, "Day high", "pos") +
    cell(L.day_low !== undefined ? fmt2(L.day_low) : null, "Day low", "neg") +
    cell(L.range_pips !== undefined ? L.range_pips + " pips" : null, "Today's range") +
    cell(L.prev_range_pips !== undefined ? L.prev_range_pips + " pips" : null, "Yesterday's range");
}

// ---- results / performance ----
let resData = null, resPeriod = (function() { try { return localStorage.getItem("resPeriod") || "7"; } catch (e) { return "7"; } })();
window._resMap = {};
async function loadResults(force, quiet) {
  try {
    if (!resData || force || Date.now() - (resData._at || 0) > 120000) {
      const d = await (await fetch("/results" + (force ? "?refresh=1" : ""))).json();
      d._at = Date.now();
      resData = d;
      window._resMap = {};
      (d.trades || []).forEach(function(t) { window._resMap[t.time_unix] = t; });
      if (typeof renderCards === "function") renderCards();
    }
    if (!quiet) renderResults();
  } catch (e) {
    if (!quiet) document.getElementById("resHero").innerHTML = '<div class="small">Could not load results. Pull to retry in a moment.</div>';
  }
}
function setResPeriod(p) {
  resPeriod = p;
  try { localStorage.setItem("resPeriod", p); } catch (e) {}
  renderResults();
}
function periodCut() {
  const now = Date.now() / 1000;
  if (resPeriod === "0") return 0;
  if (resPeriod === "1") { const ist = now + 19800; return ist - (ist % 86400) - 19800; }
  return now - parseInt(resPeriod, 10) * 86400;
}
function resultLabel(t) {
  if (t.status === "tp3") return ["TP3 ✔", "win"];
  if (t.status === "sl") return t.tp_hit === 0 ? ["SL", "loss"] : ["TP" + t.tp_hit + " → SL", t.pips > 0 ? "win" : "mixed"];
  return [t.tp_hit ? "Open · TP" + t.tp_hit + " hit" : "Open", "open"];
}
function resBadge(s) {
  if (s.kind !== "signal") return "";
  const t = window._resMap && window._resMap[s.time_unix];
  if (!t) return "";
  const lb = resultLabel(t);
  const p = t.status === "open" ? t.pips + t.float_pips : t.pips;
  return '<span class="rchip ' + lb[1] + '">' + lb[0] + " · " + sgn(p) + "p</span>";
}
function renderResults() {
  if (!resData) return;
  document.querySelectorAll("#resPeriod .chip").forEach(function(c) { c.classList.toggle("active", c.getAttribute("data-p") === resPeriod); });
  const cut = periodCut();
  const all = (resData.trades || []).filter(function(t) { return t.time_unix >= cut; });
  const closed = all.filter(function(t) { return t.status !== "open"; }).sort(function(a, b) { return a.time_unix - b.time_unix; });
  const open = all.filter(function(t) { return t.status === "open"; });
  const wins = closed.filter(function(t) { return t.pips > 0; });
  const losses = closed.filter(function(t) { return t.pips < 0; });
  const sum = function(a, k) { return a.reduce(function(s, t) { return s + t[k]; }, 0); };
  const net = sum(closed, "pips"), gw = sum(wins, "pips"), gl = Math.abs(sum(losses, "pips"));
  const netR = sum(closed, "r");
  const tp1 = all.filter(function(t) { return t.tp_hit >= 1; }).length;
  const tp2 = all.filter(function(t) { return t.tp_hit >= 2; }).length;
  const tp3 = all.filter(function(t) { return t.tp_hit >= 3; }).length;
  const fullSL = closed.filter(function(t) { return t.status === "sl" && t.tp_hit === 0; }).length;
  const slAfter = closed.filter(function(t) { return t.status === "sl" && t.tp_hit > 0; }).length;
  let cum = 0, peak = 0, dd = 0;
  const curve = closed.map(function(t) { cum += t.pips; peak = Math.max(peak, cum); dd = Math.max(dd, peak - cum); return cum; });
  const openPips = open.reduce(function(s, t) { return s + t.pips + t.float_pips; }, 0);
  const winRate = closed.length ? Math.round(100 * wins.length / closed.length) : null;
  const pf = gl > 0 ? (gw / gl).toFixed(2) : (gw > 0 ? "∞" : "-");

  document.getElementById("resUpdated").textContent = "updated " + indFmtIST(resData.updated) + " IST";
  if (!all.length) {
    document.getElementById("resHero").innerHTML = '<div class="hn neu">0</div><div class="hl">pips</div><div class="hs">No setups in this period yet. Results fill in automatically as the indicator fires.</div>';
  } else {
    document.getElementById("resHero").innerHTML =
      '<div class="hl">NET RESULT (CLOSED TRADES)</div><div class="hn ' + cls(net) + '">' + sgn(net) + '</div><div class="hl">pips · ' + sgn(netR, 2) + 'R · about ' + (net >= 0 ? "+" : "-") + "$" + Math.abs(net).toFixed(0) + " at 0.10 lot</div>" +
      '<div class="hs">' + closed.length + " closed · " + open.length + " open" + (open.length ? " (running " + sgn(openPips) + " pips)" : "") + "</div>";
  }
  const kc = function(v, l, c) { return '<div class="kcell"><div class="kv ' + (c || "") + '">' + v + '</div><div class="kl">' + l + "</div></div>"; };
  document.getElementById("resGrid").innerHTML =
    kc(all.length, "Setups") + kc(winRate === null ? "-" : winRate + "%", "Win rate", winRate !== null && winRate >= 50 ? "pos" : "neg") +
    kc(tp1, "Hit TP1", "pos") + kc(tp2, "Hit TP2", "pos") +
    kc(tp3, "Hit TP3", "pos") + kc(fullSL, "Stopped out", "neg") + kc(slAfter, "TP then SL", "neu") + kc(open.length, "Still open", "neu");

  const W = 320, H = 110;
  if (curve.length < 2) {
    document.getElementById("resCurve").innerHTML = '<div class="small">The curve appears after two closed trades.</div>';
  } else {
    const pts = [0].concat(curve);
    const mn = Math.min.apply(null, pts), mx = Math.max.apply(null, pts), span = (mx - mn) || 1;
    const xy = pts.map(function(v, i) { return [10 + i * (W - 20) / (pts.length - 1), H - 12 - (v - mn) / span * (H - 24)]; });
    const line = xy.map(function(p) { return p[0].toFixed(1) + "," + p[1].toFixed(1); }).join(" ");
    const zy = H - 12 - (0 - mn) / span * (H - 24);
    const col = curve[curve.length - 1] >= 0 ? "#3fb950" : "#f85149";
    document.getElementById("resCurve").innerHTML =
      '<svg viewBox="0 0 ' + W + " " + H + '" width="100%" style="display:block"><line x1="10" x2="' + (W - 10) + '" y1="' + zy.toFixed(1) + '" y2="' + zy.toFixed(1) + '" stroke="var(--border)" stroke-dasharray="3 3"/><polyline points="' + line + '" fill="none" stroke="' + col + '" stroke-width="2.2" stroke-linejoin="round"/><circle cx="' + xy[xy.length - 1][0].toFixed(1) + '" cy="' + xy[xy.length - 1][1].toFixed(1) + '" r="3.5" fill="' + col + '"/></svg>';
  }
  const dr = function(l, v, c) { return '<div class="drow"><span>' + l + '</span><b class="' + (c || "") + '">' + v + "</b></div>"; };
  const avgW = wins.length ? gw / wins.length : 0, avgL = losses.length ? gl / losses.length : 0;
  document.getElementById("resRows").innerHTML =
    dr("Pips won", "+" + gw.toFixed(1), "pos") + dr("Pips lost to stop losses", "-" + gl.toFixed(1), "neg") +
    dr("Profit factor", pf) + dr("Average win", "+" + avgW.toFixed(1) + " pips", "pos") + dr("Average loss", "-" + avgL.toFixed(1) + " pips", "neg") +
    dr("Best trade", closed.length ? sgn(Math.max.apply(null, closed.map(function(t) { return t.pips; }))) + " pips" : "-") +
    dr("Worst trade", closed.length ? sgn(Math.min.apply(null, closed.map(function(t) { return t.pips; }))) + " pips" : "-") +
    dr("Max drawdown", "-" + dd.toFixed(1) + " pips", dd > 0 ? "neg" : "") +
    (resData.untracked ? dr("Not counted (no price history)", resData.untracked) : "");
  document.getElementById("resLog").innerHTML = all.length ? all.slice(0, 60).map(function(t) {
    const lb = resultLabel(t);
    const p = t.status === "open" ? t.pips + t.float_pips : t.pips;
    return '<div class="logrow"><div><span class="rchip ' + (t.signal === "BUY" ? "win" : "loss") + '">' + t.signal + '</span> <b style="font-size:13px">' + fmt2(t.entry) + '</b><div class="lt">' + indFmtIST(t.time_unix) + " IST · risk " + t.risk_pips + " pips</div></div>" +
      '<div style="text-align:right"><span class="rchip ' + lb[1] + '">' + lb[0] + '</span><div class="' + cls(p) + '" style="font-weight:800;margin-top:3px">' + sgn(p) + " pips</div></div></div>";
  }).join("") : '<div class="small">Nothing to show for this period.</div>';
}

// ---- tools ----
let calcReady = false;
function initCalc() {
  if (calcReady) return;
  calcReady = true;
  const get = function(k, d) { try { return localStorage.getItem(k) || d; } catch (e) { return d; } };
  document.getElementById("cBal").value = get("cBal", "1000");
  document.getElementById("cRisk").value = get("cRisk", "1");
  document.getElementById("pLots").value = get("pLots", "0.10");
  document.getElementById("pPips").value = "100";
  calcPips();
}
function fillFromSetup() {
  const L = window._indData && window._indData.latest;
  if (!L) { document.getElementById("cOut").textContent = "No setup loaded yet. Open the Chart tab first."; return; }
  document.getElementById("cEntry").value = L.entry;
  document.getElementById("cSL").value = L.sl;
  calcLots();
}
function calcLots() {
  const bal = parseFloat(document.getElementById("cBal").value), rk = parseFloat(document.getElementById("cRisk").value);
  const e = parseFloat(document.getElementById("cEntry").value), s = parseFloat(document.getElementById("cSL").value);
  try { localStorage.setItem("cBal", bal); localStorage.setItem("cRisk", rk); } catch (x) {}
  const out = document.getElementById("cOut");
  if (!(bal > 0 && rk > 0 && e > 0 && s > 0) || e === s) { out.textContent = "Enter balance, risk %, entry and stop loss."; return; }
  const dist = Math.abs(e - s), riskUsd = bal * rk / 100;
  const lots = Math.floor(riskUsd / (dist * 100) * 100) / 100;
  const perR = lots * 100 * dist;
  out.innerHTML = "<b>Lot size: " + lots.toFixed(2) + "</b><br>Stop distance: " + (dist / 0.1).toFixed(1) + " pips ($" + dist.toFixed(2) + ")<br>Money at risk: $" + (lots * 100 * dist).toFixed(2) + " (" + rk + "% of $" + bal + ")<br>Full plan if TP3 is reached: about +$" + (perR * 2).toFixed(2) + " (+2R)";
  if (lots < 0.01) out.innerHTML += '<br><span class="neg">Below the 0.01 minimum lot: lower the risk or widen the balance.</span>';
}
function calcPips() {
  const p = parseFloat(document.getElementById("pPips").value), l = parseFloat(document.getElementById("pLots").value);
  try { localStorage.setItem("pLots", l); } catch (x) {}
  document.getElementById("pOut").innerHTML = (p > 0 || p < 0) && l > 0 ? "<b>$" + (p * l * 10).toFixed(2) + "</b> for " + p + " pips at " + l + " lot" : "-";
}

// ============= GOLD INDICATOR CHART (in-app) =============
let indBuilt = false, indTimer = null, indChart = null, indCandles = null, indHi = null, indLo = null, indLevelSeries = [], indFirstFit = true;
let indTF = (function() { try { return localStorage.getItem("indTF") || "15"; } catch (e) { return "15"; } })();
function paintIndTF() {
  document.querySelectorAll("#indTFBar button").forEach(function(b) { b.classList.toggle("active", b.getAttribute("data-tf") === indTF); });
}
function setIndTF(tf) {
  indTF = tf;
  try { localStorage.setItem("indTF", tf); } catch (e) {}
  indFirstFit = true;
  paintIndTF();
  loadIndData();
}
const IND_MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
function indPad(n) { return n < 10 ? "0" + n : "" + n; }
function indFmtIST(ts) {
  const d = new Date((ts + 19800) * 1000);
  return d.getUTCDate() + " " + IND_MON[d.getUTCMonth()] + " " + indPad(d.getUTCHours()) + ":" + indPad(d.getUTCMinutes());
}
function indColors(t) {
  const l = t === "light";
  return { bg: l ? "#ffffff" : "#131722", tx: l ? "#16181d" : "#d1d4dc", gr: l ? "#e2e6ea" : "#242832" };
}
function indApplyTheme(t) {
  if (!indChart) return;
  const c = indColors(t);
  indChart.applyOptions({ layout: { background: { color: c.bg }, textColor: c.tx }, grid: { vertLines: { color: c.gr }, horzLines: { color: c.gr } } });
}

function initIndChart() {
  function build() {
    if (indBuilt) { loadIndData(); startIndTimer(); return; }
    indBuilt = true;
    const c = indColors(document.documentElement.getAttribute("data-theme") || "dark");
    indChart = LightweightCharts.createChart(document.getElementById("indChartContainer"), {
      layout: { background: { color: c.bg }, textColor: c.tx },
      grid: { vertLines: { color: c.gr }, horzLines: { color: c.gr } },
      rightPriceScale: { borderVisible: false },
      timeScale: {
        timeVisible: true, secondsVisible: false, rightOffset: 6, borderVisible: false,
        tickMarkFormatter: function(time, type) {
          const d = new Date((time + 19800) * 1000);
          if (type <= 2) return d.getUTCDate() + " " + IND_MON[d.getUTCMonth()];
          return indPad(d.getUTCHours()) + ":" + indPad(d.getUTCMinutes());
        }
      },
      localization: { timeFormatter: function(time) { return indFmtIST(time) + " IST"; } },
      autoSize: true
    });
    indCandles = indChart.addCandlestickSeries({
      upColor: "#26a69a", downColor: "#ef5350", borderVisible: false,
      wickUpColor: "#26a69a", wickDownColor: "#ef5350"
    });
    indHi = indChart.addLineSeries({ color: "#ff9800", lineWidth: 1, lineStyle: 2, lineType: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    indLo = indChart.addLineSeries({ color: "#42a5f5", lineWidth: 1, lineStyle: 2, lineType: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    loadIndData();
    startIndTimer();
  }
  if (lwScriptLoaded) { build(); return; }
  const s = document.createElement("script");
  s.src = "https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js";
  s.onload = function() { lwScriptLoaded = true; build(); };
  document.body.appendChild(s);
}

function startIndTimer() {
  if (indTimer) return;
  indTimer = setInterval(function() {
    if (document.getElementById("indCard").style.display !== "none") loadIndData();
  }, 60000);
}

let indLvlLines = [];
function renderPlan() {
  const data = window._indData;
  const info = document.getElementById("indInfo");
  if (!data || !info) return;
  const L = data.latest;
  const price = livePrice || data.price;
  if (!L) {
    info.innerHTML = '<div class="ind-head"><span class="ind-chip neutral">No setup in the loaded window</span></div><div style="color:var(--muted);font-size:11px">Last price ' + fmt2(price) + "</div>";
    return;
  }
  const buy = L.signal === "BUY", sign = buy ? 1 : -1;
  const risk = Math.abs(L.entry - L.sl);
  const fpips = (price - L.entry) * sign / 0.1;
  const fr = (price - L.entry) * sign / risk;
  const st = L.status || "Active";
  const stColor = st === "Active" ? "var(--accent)" : (st.indexOf("SL") >= 0 ? "var(--sell)" : "var(--buy)");
  const span = L.tp3 - L.sl;
  const pos = function(v) { return Math.max(0, Math.min(100, (v - L.sl) / span * 100)); };
  info.innerHTML =
    '<div class="ind-head"><span class="ind-chip ' + (buy ? "buy" : "sell") + '">' + (buy ? "▲ BULLISH · BUY" : "▼ BEARISH · SELL") + "</span>" +
    '<span style="color:var(--muted)">Setup ' + indFmtIST(L.time_unix) + ' IST · <b style="color:' + stColor + '">' + st + "</b></span></div>" +
    '<div class="ind-grid">' +
    '<div class="ind-cell"><div class="v">' + fmt2(L.entry) + '</div><div class="l">Entry</div></div>' +
    '<div class="ind-cell"><div class="v" style="color:var(--sell)">' + fmt2(L.sl) + '</div><div class="l">SL</div></div>' +
    '<div class="ind-cell"><div class="v" style="color:var(--buy)">' + fmt2(L.tp1) + '</div><div class="l">TP1</div></div>' +
    '<div class="ind-cell"><div class="v" style="color:var(--buy)">' + fmt2(L.tp2) + '</div><div class="l">TP2</div></div>' +
    '<div class="ind-cell"><div class="v" style="color:var(--buy)">' + fmt2(L.tp3) + '</div><div class="l">TP3</div></div>' +
    "</div>" +
    '<div class="plan-bar"><div class="tick" style="left:0"></div><div class="tl" style="left:0%">SL</div>' +
    '<div class="tick" style="left:' + pos(L.entry) + '%"></div><div class="tl" style="left:' + pos(L.entry) + '%">Entry</div>' +
    '<div class="tick" style="left:' + pos(L.tp1) + '%"></div><div class="tl" style="left:' + pos(L.tp1) + '%">TP1</div>' +
    '<div class="tick" style="left:' + pos(L.tp2) + '%"></div><div class="tl" style="left:' + pos(L.tp2) + '%">TP2</div>' +
    '<div class="tick" style="left:100%"></div><div class="tl" style="left:97%">TP3</div>' +
    '<div class="you" style="left:' + pos(price) + '%"></div></div>' +
    '<div class="drow"><span>Live price</span><b>' + fmt2(price) + "</b></div>" +
    '<div class="drow"><span>Floating on this setup</span><b class="' + cls(fpips) + '">' + sgn(fpips) + " pips (" + sgn(fr, 2) + "R)</b></div>" +
    '<div class="drow"><span>Risk on this setup</span><b>' + (L.risk_pips !== undefined ? L.risk_pips : (risk / 0.1).toFixed(1)) + " pips</b></div>";
}

async function loadIndData() {
  const info = document.getElementById("indInfo");
  try {
    paintIndTF();
    const res = await fetch("/indicator-data?tf=" + indTF);
    const data = await res.json();
    const bars = data.bars || [];
    if (!bars.length) { info.textContent = "No candle data yet (" + (data.error || "waiting for first update") + ")."; return; }
    window._indData = data;
    indCandles.setData(bars);
    indHi.setData(data.struct_high || []);
    indLo.setData(data.struct_low || []);
    const firstT = bars[0].time, lastT = bars[bars.length - 1].time;
    const per = data.period || 900;

    const markers = [];
    (data.events || []).forEach(function(ev) {
      const t = ev.time_unix - (ev.time_unix % per);
      if (t < firstT) return;
      const buy = ev.signal === "BUY";
      if (ev.kind === "signal") {
        markers.push({ time: t, position: buy ? "belowBar" : "aboveBar", color: buy ? "#3fb950" : "#f85149", shape: buy ? "arrowUp" : "arrowDown", text: ev.signal });
      } else {
        markers.push({ time: t, position: buy ? "belowBar" : "aboveBar", color: "#d4af37", shape: "circle", text: "" });
      }
    });
    markers.sort(function(a, b) { return a.time - b.time; });
    indCandles.setMarkers(markers);

    indLevelSeries.forEach(function(s) { indChart.removeSeries(s); });
    indLevelSeries = [];
    const L = data.latest;
    if (L) {
      const t1 = Math.max(L.time_unix - (L.time_unix % per), firstT);
      const defs = [["Entry", L.entry, "#2962ff", 0, 2], ["SL", L.sl, "#f85149", 0, 2], ["TP1", L.tp1, "#3fb950", 2, 1], ["TP2", L.tp2, "#3fb950", 2, 1], ["TP3", L.tp3, "#3fb950", 2, 1]];
      defs.forEach(function(d) {
        const s = indChart.addLineSeries({ color: d[2], lineWidth: d[4], lineStyle: d[3], priceLineVisible: false, lastValueVisible: true, title: d[0], crosshairMarkerVisible: false });
        s.setData(t1 < lastT ? [{ time: t1, value: d[1] }, { time: lastT, value: d[1] }] : [{ time: lastT, value: d[1] }]);
        indLevelSeries.push(s);
      });
    }
    indLvlLines.forEach(function(pl) { indCandles.removePriceLine(pl); });
    indLvlLines = [];
    const LV = data.levels || {};
    [["PDH", LV.pdh], ["PDL", LV.pdl]].forEach(function(x) {
      if (x[1] !== undefined && x[1] !== null) indLvlLines.push(indCandles.createPriceLine({ price: x[1], color: "#9aa4b2", lineWidth: 1, lineStyle: 3, axisLabelVisible: true, title: x[0] }));
    });
    fillCtx(LV);
    if (indFirstFit) {
      indFirstFit = false;
      const n = bars.length;
      indChart.timeScale().setVisibleLogicalRange({ from: Math.max(0, n - 110), to: n + 6 });
    }
    document.getElementById("indUpdated").textContent = (data.market_closed ? "Market closed · " : "") + "updated " + indFmtIST(data.updated || lastT) + " IST";
    renderPlan();
  } catch (e) {
    info.textContent = "Could not load indicator data. It will retry automatically.";
  }
}

function selectChart(which) {
  localStorage.setItem("chartChoice", which);
  closeChooser();
  paintViewSeg(which);
  document.getElementById("tvCard").style.display = which === "tv" ? "" : "none";
  document.getElementById("setupsCard").style.display = which === "setups" ? "" : "none";
  document.getElementById("indCard").style.display = which === "ind" ? "" : "none";
  if (which === "tv") {
    document.getElementById("tvSymbolSelect").value = currentTVSymbol;
    const label = currentTVSymbol.replace("FOREXCOM:", "");
    document.getElementById("tvChartTitle").textContent = label === "XAUUSD" ? "XAUUSD" : label.slice(0,3) + "/" + label.slice(3);
    initTVWidget(document.documentElement.getAttribute("data-theme") || "dark");
  } else if (which === "ind") {
    initIndChart();
  } else {
    initSetupsChart();
  }
}

function initSetupsChart() {
  function build() {
    if (setupsChartBuilt) { loadSetupsData(); return; }
    setupsChartBuilt = true;
    const theme = document.documentElement.getAttribute("data-theme") || "dark";
    const isLight = theme === "light";
    window._lwChart = LightweightCharts.createChart(document.getElementById("setupsChartContainer"), {
      layout: { background: { color: isLight ? "#ffffff" : "#131722" }, textColor: isLight ? "#16181d" : "#d1d4dc" },
      grid: { vertLines: { color: isLight ? "#e2e6ea" : "#242832" }, horzLines: { color: isLight ? "#e2e6ea" : "#242832" } },
      timeScale: { timeVisible: true, secondsVisible: false },
      autoSize: true
    });
    window._lwSeries = window._lwChart.addCandlestickSeries({
      upColor: "#26a69a", downColor: "#ef5350", borderVisible: false,
      wickUpColor: "#26a69a", wickDownColor: "#ef5350"
    });
    window._lwChart.subscribeClick(function(param) {
      showSetupTooltip(param);
    });
    loadSetupsData();
  }
  if (lwScriptLoaded) { build(); return; }
  const s = document.createElement("script");
  s.src = "https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js";
  s.onload = function() { lwScriptLoaded = true; build(); };
  document.body.appendChild(s);
}

async function loadSetupsData() {
  try {
    const res = await fetch("/candles");
    const data = await res.json();
    const bars = data.bars || [];
    if (bars.length === 0) return;
    window._lwSeries.setData(bars);

    const withTime = allSignals.filter(s => s.kind === "signal" && s.time_unix);
    const markers = withTime.map(s => ({
      time: s.time_unix,
      position: s.signal === "BUY" ? "belowBar" : "aboveBar",
      color: s.signal === "BUY" ? "#3fb950" : "#f85149",
      shape: s.signal === "BUY" ? "arrowUp" : "arrowDown",
      text: s.signal
    })).sort((a, b) => a.time - b.time);
    window._lwSeries.setMarkers(markers);
    window._lwSignals = withTime;

    window._lwSeries.priceLines?.forEach(pl => window._lwSeries.removePriceLine(pl));
    window._lwSeries.priceLines = [];
    if (withTime.length > 0) {
      const latest = withTime[withTime.length - 1];
      const lines = [
        [parseFloat(latest.entry), "#2962ff", "Entry"],
        [parseFloat(latest.sl), "#f85149", "SL"],
        [parseFloat(latest.tp1), "#3fb950", "TP1"],
        [parseFloat(latest.tp2), "#3fb950", "TP2"],
        [parseFloat(latest.tp3), "#3fb950", "TP3"]
      ];
      lines.forEach(([price, color, title]) => {
        const pl = window._lwSeries.createPriceLine({ price, color, lineWidth: 1, lineStyle: 2, title });
        window._lwSeries.priceLines.push(pl);
      });
    }
    window._lwChart.timeScale().fitContent();
  } catch (e) {
    console.log("Setups chart load failed", e);
  }
}

function showSetupTooltip(param) {
  const tip = document.getElementById("setupsTooltip");
  if (!param.time || !window._lwSignals || window._lwSignals.length === 0) {
    tip.style.display = "none";
    return;
  }
  let closest = null, closestDiff = Infinity;
  window._lwSignals.forEach(s => {
    const diff = Math.abs(s.time_unix - param.time);
    if (diff < closestDiff) { closestDiff = diff; closest = s; }
  });
  if (!closest || closestDiff > 3600 * 6) {
    tip.style.display = "none";
    return;
  }
  tip.innerHTML = `
    <div class="t-title">${closest.signal} - ${closest.time}</div>
    <div class="t-row"><span class="t-label">Entry</span><span>${closest.entry}</span></div>
    <div class="t-row"><span class="t-label">SL</span><span>${closest.sl}</span></div>
    <div class="t-row"><span class="t-label">TP1</span><span>${closest.tp1}</span></div>
    <div class="t-row"><span class="t-label">TP2</span><span>${closest.tp2}</span></div>
    <div class="t-row"><span class="t-label">TP3</span><span>${closest.tp3}</span></div>
  `;
  tip.style.left = Math.min(param.point.x, 160) + "px";
  tip.style.top = "10px";
  tip.style.display = "block";
}

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) outputArray[i] = rawData.charCodeAt(i);
  return outputArray;
}

function updateNotifyBtn() {
  const btn = document.getElementById("notifyBtn");
  if (!("Notification" in window)) { btn.style.display = "none"; return; }
  if (Notification.permission === "granted") {
    btn.textContent = "🔔";
    btn.title = "Notifications enabled";
  } else {
    btn.textContent = "🔕";
    btn.title = "Tap to enable notifications";
  }
}

async function enablePush() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    alert("Push notifications aren't supported in this browser.");
    return;
  }
  if (Notification.permission === "denied") {
    alert("Notifications were previously blocked for this site. Your browser won't ask again automatically.\n\nTo fix: tap the lock/info icon next to the address bar → Site settings → Notifications → set to Allow, then reload this page and tap the bell again.");
    return;
  }
  try {
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
      alert("Notification permission was not granted, so alerts can't be enabled right now.");
      updateNotifyBtn();
      return;
    }
    const reg = await navigator.serviceWorker.ready;
    const keyRes = await fetch("/vapid-public-key");
    const keyData = await keyRes.json();
    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(keyData.key)
      });
    }
    await fetch("/subscribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(sub)
    });
    updateNotifyBtn();
  } catch (e) {
    console.log("Push subscribe failed", e);
    alert("Could not enable notifications: " + (e && e.message ? e.message : e));
  }
  updateNotifyBtn();
  refreshSettingsPanel();
}

let savedChoice = localStorage.getItem("chartChoice");
if (!localStorage.getItem("indDefaultV1")) { savedChoice = "ind"; localStorage.setItem("indDefaultV1", "1"); }
if (savedChoice) {
  selectChart(savedChoice);
} else {
  openChooser();
}

applyTheme(localStorage.getItem("theme") || "dark");

function timeAgo(iso) {
  return iso;
}

function renderStats() {
  const total = allSignals.length;
  const buys = allSignals.filter(s => s.signal === "BUY").length;
  const sells = allSignals.filter(s => s.signal === "SELL").length;
  document.getElementById("statsStrip").innerHTML = `
    <div class="stat-pill"><div class="num">${total}</div><div class="lbl">Total</div></div>
    <div class="stat-pill buy"><div class="num">${buys}</div><div class="lbl">Buy</div></div>
    <div class="stat-pill sell"><div class="num">${sells}</div><div class="lbl">Sell</div></div>
  `;
}

function renderFilters() {
  const opts = [["all","All"],["BUY","Buy"],["SELL","Sell"],["signal","New Setup"],["touch","Zone Touch"]];
  document.getElementById("filters").innerHTML = opts.map(([key,label]) =>
    `<div class="chip ${currentFilter===key?'active':''}" onclick="setFilter('${key}')">${label}</div>`
  ).join("");
}

function setFilter(key) {
  currentFilter = key;
  renderFilters();
  renderCards();
}

function renderCards() {
  const el = document.getElementById("content");
  let list = allSignals;
  if (currentFilter === "BUY" || currentFilter === "SELL") list = list.filter(s => s.signal === currentFilter);
  if (currentFilter === "signal" || currentFilter === "touch") list = list.filter(s => s.kind === currentFilter);

  if (list.length === 0) {
    el.innerHTML = '<div class="empty"><div class="emoji">\ud83d\udcc9</div>No signals match this filter yet.</div>';
    return;
  }
  let html = "";
  list.forEach((s, i) => {
    const badgeClass = s.signal === "BUY" ? "buy" : "sell";
    const arrow = s.signal === "BUY" ? "\u2191" : "\u2193";
    const kindLabel = s.kind === "touch" ? "Zone Re-Touch" : "New Setup";
    html += `
      <a class="card-link" href="https://www.tradingview.com/chart/?symbol=FOREXCOM:XAUUSD" target="_blank" rel="noopener">
      <div class="card" style="animation-delay:${Math.min(i,10)*0.04}s">
        <img src="${s.chart_url}" loading="lazy">
        <div class="card-body">
          <div class="badge-row">
            <span class="badge ${badgeClass}">${arrow} ${s.signal}</span>
            <span style="display:flex;gap:6px;align-items:center">${resBadge(s)}<span class="kind-tag">${kindLabel}</span></span>
          </div>
          <div class="rows">
            <div class="row entry"><span class="label">Entry</span><span class="value">${s.entry}</span></div>
            <div class="row sl"><span class="label">Stop Loss</span><span class="value">${s.sl}</span></div>
            <div class="row tp"><span class="label">TP1</span><span class="value">${s.tp1}</span></div>
            <div class="row tp"><span class="label">TP2</span><span class="value">${s.tp2}</span></div>
            <div class="row tp"><span class="label">TP3</span><span class="value">${s.tp3}</span></div>
          </div>
        </div>
        <div class="time">${s.symbol} \u2022 ${s.time}</div>
        <div class="tap-hint">\ud83d\udcc8 Tap to open on TradingView</div>
      </div>
      </a>`;
  });
  el.innerHTML = html;
}

async function loadWeekStats() {
  try {
    const res = await fetch("/stats7d");
    const s = await res.json();
    const grid = document.getElementById("weekGrid");
    const cells = grid.querySelectorAll(".week-cell .num");
    cells[0].textContent = s.total;
    cells[1].textContent = s.sl_hit;
    cells[2].textContent = s.tp_hit;
    cells[3].textContent = s.open;
    const note = document.getElementById("weekNote");
    if (s.total === 0) {
      note.innerHTML = "No setups yet in the last 7 days - this fills in automatically once your indicator fires a signal.";
    } else {
      let parts = [];
      if (s.win_rate !== null && s.win_rate !== undefined) parts.push(`Win rate: <b>${s.win_rate}%</b>`);
      if (s.avg_mfe_r !== null && s.avg_mfe_r !== undefined) parts.push(`Avg best move: <b>${s.avg_mfe_r}R</b>`);
      if (s.avg_mae_r !== null && s.avg_mae_r !== undefined) parts.push(`Avg worst move: <b>${s.avg_mae_r}R</b>`);
      if (s.avg_mfe_r_on_losses !== null && s.avg_mfe_r_on_losses !== undefined) {
        parts.push(`Losers moved <b>${s.avg_mfe_r_on_losses}R</b> in your favor before reversing`);
      }
      if (s.untracked > 0) parts.push(`${s.untracked} not counted (no price history)`);
      note.innerHTML = parts.join(" · ") || "";
    }
  } catch (e) {
    document.getElementById("weekNote").textContent = "Could not load weekly results.";
  }
}

let lastSeenSignalKey = null;
function playAlertSound() {
  if (localStorage.getItem("soundEnabled") === "off") return;
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
    osc.start();
    osc.stop(ctx.currentTime + 0.4);
  } catch (e) {}
}

async function load(manual) {
  try {
    const res = await fetch("/latest");
    const data = await res.json();
    allSignals = (data.signals || []).filter(function(s) { return !(s.entry === "DUMMY" || (String(s.entry) === "4000.00" && String(s.sl) === "3990.00")); });
    if (allSignals.length > 0) {
      const topKey = allSignals[0].time + allSignals[0].signal + allSignals[0].kind;
      if (lastSeenSignalKey !== null && topKey !== lastSeenSignalKey) {
        playAlertSound();
      }
      lastSeenSignalKey = topKey;
    }
    renderStats();
    renderFilters();
    renderCards();
  } catch (e) {
    document.getElementById("content").innerHTML = '<div class="empty"><div class="emoji">\u26a0\ufe0f</div>Could not load signals. It will retry automatically.</div>';
  }
}

async function loadTicker() {
  try {
    const res = await fetch("/crypto-ticker");
    const data = await res.json();
    const coins = data.coins || [];
    if (coins.length === 0) return;
    const itemHtml = (c) => {
      const dir = c.change_pct >= 0 ? "up" : "down";
      const arrow = c.change_pct >= 0 ? "▲" : "▼";
      const priceStr = c.price >= 1 ? c.price.toLocaleString(undefined, {maximumFractionDigits: 2}) : c.price.toPrecision(4);
      const tag = c.type === "gainer" ? '<span class="tgainer-tag">TOP GAINER</span>' : "";
      const name = c.symbol;
      return `<span class="ticker-item">${tag}<span class="tsym">${name}</span><span class="tprice">$${priceStr}</span><span class="tchange ${dir}">${arrow} ${Math.abs(c.change_pct).toFixed(2)}%</span></span>`;
    };
    // Render the list twice back-to-back so the CSS animation (translateX -50%) loops seamlessly
    const html = coins.map(itemHtml).join("") + coins.map(itemHtml).join("");
    document.getElementById("tickerTrack").innerHTML = html;
  } catch (e) {
    // leave existing ticker content in place on a transient failure
  }
}

async function loadForexTicker() {
  try {
    const res = await fetch("/forex-ticker");
    const data = await res.json();
    const pairs = data.pairs || [];
    if (pairs.length === 0) return;
    const itemHtml = (p) => {
      const dir = p.change_pct >= 0 ? "up" : "down";
      const arrow = p.change_pct >= 0 ? "▲" : "▼";
      const decimals = p.price >= 10 ? 3 : 5;
      const priceStr = p.price.toFixed(decimals);
      return `<span class="ticker-item"><span class="tsym">${p.symbol}</span><span class="tprice">${priceStr}</span><span class="tchange ${dir}">${arrow} ${Math.abs(p.change_pct).toFixed(2)}%</span></span>`;
    };
    const html = pairs.map(itemHtml).join("") + pairs.map(itemHtml).join("");
    document.getElementById("forexTickerTrack").innerHTML = html;
  } catch (e) {
    // leave existing ticker content in place on a transient failure
  }
}

load();
loadTicker();
loadForexTicker();
setInterval(load, 20000);
setInterval(loadTicker, 120000);
setInterval(loadForexTicker, 600000);
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(()=>{});
}
updateNotifyBtn();
pollPrice();
renderSessions();
showTab((function() { try { return localStorage.getItem("tab") || "chart"; } catch (e) { return "chart"; } })());
</script>
</body>
</html>"""
    return Response(html, mimetype="text/html")


@app.route("/manifest.json", methods=["GET"])
def manifest():
    m = {
        "name": "Bullion Radar",
        "short_name": "Bullion Radar",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0d1117",
        "theme_color": "#0d1117",
        "icons": [
            {"src": "/icon192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon512.png", "sizes": "512x512", "type": "image/png"}
        ]
    }
    return Response(json.dumps(m), mimetype="application/json")


@app.route("/sw.js", methods=["GET"])
def sw():
    js = """
self.addEventListener('fetch', function(e){});
self.addEventListener('install', function(e){ self.skipWaiting(); });
self.addEventListener('activate', function(e){ e.waitUntil(clients.claim()); });

self.addEventListener('push', function(event) {
  let data = { title: 'Bullion Radar', body: 'New signal available', url: '/' };
  try { data = event.data.json(); } catch (e) {}
  const options = {
    body: data.body,
    icon: '/icon192.png',
    badge: '/badge.png',
    vibrate: [300, 150, 300, 150, 600],
    data: { url: data.url || '/' }
  };
  event.waitUntil(self.registration.showNotification(data.title, options));
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  const url = event.notification.data && event.notification.data.url ? event.notification.data.url : '/';
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(function(clientList) {
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});
"""
    return Response(js, mimetype="application/javascript")


@app.route("/badge.png", methods=["GET"])
def badge_png():
    return Response(base64.b64decode(ICON_BADGE_B64), mimetype="image/png")


@app.route("/icon192.png", methods=["GET"])
def icon192():
    return Response(base64.b64decode(ICON_192_B64), mimetype="image/png")


@app.route("/icon512.png", methods=["GET"])
def icon512():
    return Response(base64.b64decode(ICON_512_B64), mimetype="image/png")


FOREX_CURRENCIES = {"EUR", "USD", "JPY", "GBP", "CHF", "AUD", "CAD", "NZD"}
FF_NOTIFIED_PATH = "data/ff_notified.json"
FF_SETTINGS_PATH = "data/ff_settings.json"
FF_ALERT_WINDOW_SECONDS = 15 * 60  # matches the ~15-min external check interval

_ff_cache = {"data": None, "ts": 0}
FF_CACHE_TTL = 1800  # 30 min - Forex Factory limits their feed to 2 requests/5min


def fetch_forex_calendar():
    import time as _time
    now = _time.time()
    if _ff_cache["data"] is not None and (now - _ff_cache["ts"]) < FF_CACHE_TTL:
        return _ff_cache["data"]
    try:
        r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=20)
        r.raise_for_status()
        raw = r.json()
    except Exception as e:
        print("Forex Factory calendar fetch failed:", repr(e))
        return _ff_cache["data"] if _ff_cache["data"] is not None else []

    events = []
    for e in raw:
        if e.get("country") not in FOREX_CURRENCIES:
            continue
        try:
            dt = datetime.fromisoformat(e["date"])
        except Exception:
            continue
        events.append({
            "title": e.get("title", ""), "country": e["country"], "impact": e.get("impact", ""),
            "forecast": e.get("forecast", ""), "previous": e.get("previous", ""),
            "date_iso": dt.isoformat(), "time_unix": int(dt.timestamp()),
        })
    events.sort(key=lambda x: x["time_unix"])
    _ff_cache["data"] = events
    _ff_cache["ts"] = now
    return events


@app.route("/forex-news", methods=["GET"])
def forex_news():
    events = fetch_forex_calendar()
    now_unix = int(datetime.now(timezone.utc).timestamp())
    upcoming = [e for e in events if e["time_unix"] >= now_unix - 3600]
    return Response(json.dumps({"events": upcoming}), mimetype="application/json")


@app.route("/forex-alerts-setting", methods=["GET", "POST"])
def forex_alerts_setting():
    settings, sha = gh_load_json(FF_SETTINGS_PATH)
    current = settings[0] if isinstance(settings, list) and settings else {"enabled": True}
    if request.method == "GET":
        return Response(json.dumps(current), mimetype="application/json")
    body = request.get_json(silent=True) or {}
    current = {"enabled": bool(body.get("enabled", True))}
    gh_save_json(FF_SETTINGS_PATH, [current], sha)
    return Response(json.dumps(current), mimetype="application/json")


@app.route("/check-forex-news", methods=["GET"])
def check_forex_news():
    settings, _ = gh_load_json(FF_SETTINGS_PATH)
    enabled = True
    if isinstance(settings, list) and settings:
        enabled = bool(settings[0].get("enabled", True))
    if not enabled:
        return json.dumps({"skipped": "alerts disabled"}), 200

    events = fetch_forex_calendar()
    now_unix = int(datetime.now(timezone.utc).timestamp())
    imminent = [
        e for e in events
        if e["impact"] == "High" and now_unix <= e["time_unix"] <= now_unix + FF_ALERT_WINDOW_SECONDS
    ]
    if not imminent:
        return json.dumps({"checked": len(events), "notified": 0}), 200

    notified_list, sha = gh_load_json(FF_NOTIFIED_PATH)
    if not isinstance(notified_list, list):
        notified_list = []
    notified_keys = set(notified_list)
    cutoff = now_unix - 7 * 24 * 3600
    notified_list = [k for k in notified_list if int(k.split("|")[-1]) >= cutoff]

    sent = 0
    for e in imminent:
        key = f"{e['country']}|{e['title']}|{e['time_unix']}"
        if key in notified_keys:
            continue
        try:
            send_push_to_all(
                f"📰 {e['country']} High Impact: {e['title']}",
                f"Forecast {e['forecast'] or 'N/A'} | Previous {e['previous'] or 'N/A'}",
                "/news"
            )
            notified_list.append(key)
            sent += 1
        except Exception as ex:
            print("Forex news push failed for", key, ":", repr(ex))

    gh_save_json(FF_NOTIFIED_PATH, notified_list, sha)
    return json.dumps({"checked": len(events), "notified": sent}), 200


@app.route("/news", methods=["GET"])
def forex_news_page():
    html = r"""<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Forex News</title>
<style>
body { background:#0f1115; color:#eee; font-family:-apple-system,sans-serif; padding:16px; margin:0; }
h2 { margin:0 0 4px; font-size:20px; }
.sub { color:#888; font-size:12px; margin-bottom:14px; }
.toggle-row { display:flex; justify-content:space-between; align-items:center; background:#1a1d24; border:1px solid #2a2e39; border-radius:12px; padding:12px 14px; margin-bottom:16px; }
.toggle { width:44px; height:26px; border-radius:20px; background:#333; position:relative; cursor:pointer; transition:background 0.2s; }
.toggle.on { background:#2ea043; }
.toggle .knob { position:absolute; top:2px; left:2px; width:22px; height:22px; border-radius:50%; background:white; transition:transform 0.2s; }
.toggle.on .knob { transform:translateX(18px); }
.item { background:#1a1d24; border:1px solid #2a2e39; border-radius:12px; padding:12px 14px; margin-bottom:8px; }
.item .top { display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; }
.badge { font-size:11px; font-weight:700; padding:3px 8px; border-radius:6px; }
.badge.High { background:#3a1a1a; color:#ef5350; }
.badge.Medium { background:#3a2f1a; color:#f4c430; }
.badge.Low { background:#1a2a1a; color:#8fbf8f; }
.ccy { font-weight:700; font-size:12px; color:#aaa; }
.time { font-size:11px; color:#888; }
.title { font-size:13.5px; margin-top:4px; }
.fc { font-size:11.5px; color:#888; margin-top:3px; }
.empty { text-align:center; color:#888; padding:40px 0; font-size:13px; }
</style></head>
<body>
<h2>📰 Forex News</h2>
<div class="sub">High-impact economic events for EUR, USD, JPY, GBP, CHF, AUD, CAD, NZD</div>
<div class="toggle-row">
  <span>Push alerts for high-impact events</span>
  <div class="toggle" id="ffToggle" onclick="toggleAlerts()"><div class="knob"></div></div>
</div>
<div id="list"><div class="empty">Loading…</div></div>
<script>
async function loadToggle() {
  try {
    const res = await fetch("/forex-alerts-setting");
    const s = await res.json();
    document.getElementById("ffToggle").classList.toggle("on", s.enabled !== false);
  } catch (e) {}
}
async function toggleAlerts() {
  const el = document.getElementById("ffToggle");
  const newState = !el.classList.contains("on");
  el.classList.toggle("on", newState);
  await fetch("/forex-alerts-setting", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({enabled: newState})
  });
}
async function loadNews() {
  const list = document.getElementById("list");
  try {
    const res = await fetch("/forex-news");
    const data = await res.json();
    const events = data.events || [];
    if (events.length === 0) {
      list.innerHTML = '<div class="empty">No upcoming events found.</div>';
      return;
    }
    list.innerHTML = events.map(e => {
      const d = new Date(e.time_unix * 1000);
      const timeStr = d.toLocaleString(undefined, {weekday:"short", hour:"2-digit", minute:"2-digit", month:"short", day:"numeric"});
      return `<div class="item">
        <div class="top"><span class="ccy">${e.country}</span><span class="badge ${e.impact}">${e.impact || "?"}</span></div>
        <div class="title">${e.title}</div>
        <div class="fc">Forecast: ${e.forecast || "-"} · Previous: ${e.previous || "-"}</div>
        <div class="time">${timeStr}</div>
      </div>`;
    }).join("");
  } catch (e) {
    list.innerHTML = '<div class="empty">Could not load news.</div>';
  }
}
loadToggle();
loadNews();
</script>
</body></html>"""
    return Response(html, mimetype="text/html")


@app.route("/history", methods=["GET"])
def notification_history_page():
    html = r"""<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Notification History</title>
<style>
body { background:#0f1115; color:#eee; font-family:-apple-system,sans-serif; padding:16px; margin:0; }
h2 { margin:0 0 4px; font-size:20px; }
.sub { color:#888; font-size:12px; margin-bottom:16px; }
.item {
  background:#1a1d24; border:1px solid #2a2e39; border-radius:12px; padding:12px 14px; margin-bottom:10px;
}
.item .top { display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; }
.badge { font-size:11px; font-weight:700; padding:3px 8px; border-radius:6px; }
.badge.buy { background:#1a3a2e; color:#26a69a; }
.badge.sell { background:#3a1a1a; color:#ef5350; }
.badge.touch { background:#3a2f1a; color:#f4c430; }
.time { font-size:11px; color:#888; }
.detail { font-size:12.5px; color:#bbb; margin-top:4px; }
.empty { text-align:center; color:#888; padding:40px 0; font-size:13px; }
</style></head>
<body>
<h2>🔔 Notification History</h2>
<div class="sub">Every setup and zone-touch alert ever sent - useful if you missed push notifications while offline.</div>
<div id="list"><div class="empty">Loading…</div></div>
<script>
async function load() {
  const list = document.getElementById("list");
  try {
    const res = await fetch("/latest");
    const data = await res.json();
    const signals = data.signals || [];
    if (signals.length === 0) {
      list.innerHTML = '<div class="empty">No notifications yet.</div>';
      return;
    }
    list.innerHTML = signals.map(s => {
      const isTouch = s.kind === "touch";
      const badgeClass = isTouch ? "touch" : (s.signal === "BUY" ? "buy" : "sell");
      const label = isTouch ? "ZONE TOUCH" : s.signal;
      return `<div class="item">
        <div class="top"><span class="badge ${badgeClass}">${label}</span><span class="time">${s.time || ""}</span></div>
        <div class="detail">${s.symbol || "XAUUSD"} · Entry ${s.entry || "-"} · SL ${s.sl || "-"} · TP1 ${s.tp1 || "-"}</div>
      </div>`;
    }).join("");
  } catch (e) {
    list.innerHTML = '<div class="empty">Could not load history.</div>';
  }
}
load();
</script>
</body></html>"""
    return Response(html, mimetype="text/html")


@app.route("/add", methods=["GET"])
def add_form():
    html = r"""<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Add Past Setup</title>
<style>
body { background:#0f1115; color:#eee; font-family:-apple-system,sans-serif; padding:20px; }
h2 { margin-top:0; }
label { display:block; margin-top:14px; font-size:14px; color:#aaa; }
input, select { width:100%; box-sizing:border-box; padding:10px; margin-top:4px; border-radius:8px; border:1px solid #333; background:#1a1d24; color:#fff; font-size:16px; }
button { margin-top:20px; width:100%; padding:14px; border:none; border-radius:10px; background:#f4c430; color:#000; font-weight:700; font-size:16px; }
.msg { margin-top:14px; padding:10px; border-radius:8px; }
.ok { background:#1a3a1a; color:#8f8; }
.err { background:#3a1a1a; color:#f88; }
</style></head>
<body>
<h2>Add a Past Setup</h2>
<p style="color:#888;font-size:13px">Enter values exactly as shown on your TradingView chart/log for a setup that already fired.</p>
<form id="f">
  <label>Symbol</label>
  <input name="symbol" value="XAUUSD" required>
  <label>Signal</label>
  <select name="signal"><option>BUY</option><option>SELL</option></select>
  <label>Entry</label>
  <input name="entry" type="number" step="any" required>
  <label>Stop Loss</label>
  <input name="sl" type="number" step="any" required>
  <label>TP1</label>
  <input name="tp1" type="number" step="any" required>
  <label>TP2</label>
  <input name="tp2" type="number" step="any">
  <label>TP3</label>
  <input name="tp3" type="number" step="any">
  <label>Date &amp; Time it fired</label>
  <input name="datetime" type="datetime-local" required>
  <button type="submit">Add Setup</button>
</form>
<div id="result"></div>
<script>
document.getElementById("f").addEventListener("submit", async function(e){
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = Object.fromEntries(fd.entries());
  const res = document.getElementById("result");
  res.innerHTML = "";
  try {
    const r = await fetch("/add-manual-signal", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(body)
    });
    const j = await r.json();
    if (r.ok) {
      res.innerHTML = '<div class="msg ok">Added. <a href="/" style="color:#8f8">Go to app</a> or add another below.</div>';
      e.target.reset();
      document.querySelector('input[name="symbol"]').value = "XAUUSD";
    } else {
      res.innerHTML = '<div class="msg err">' + (j.error || "Failed to add") + '</div>';
    }
  } catch (err) {
    res.innerHTML = '<div class="msg err">Network error: ' + err + '</div>';
  }
});
</script>
</body></html>"""
    return Response(html, mimetype="text/html")


SWING_LEN = 5
ATR_LEN = 14
SL_BUFFER_MULT = 0.25
RR = [1.0, 2.0, 3.0]


def compute_atr(bars, length):
    atr = [None] * len(bars)
    trs = []
    for i in range(len(bars)):
        if i == 0:
            tr = bars[i]["high"] - bars[i]["low"]
        else:
            pc = bars[i - 1]["close"]
            tr = max(bars[i]["high"] - bars[i]["low"], abs(bars[i]["high"] - pc), abs(bars[i]["low"] - pc))
        trs.append(tr)
        if i + 1 >= length:
            if atr[i - 1] is None:
                atr[i] = sum(trs[i - length + 1:i + 1]) / length
            else:
                atr[i] = (atr[i - 1] * (length - 1) + tr) / length
    return atr


def find_pivots_15m(bars15, length):
    """Returns confirmed pivot events (onset_time, pivot_high_or_None, pivot_low_or_None).
    onset_time is 'length' bars after the pivot bar itself, matching request.security(lookahead_off)
    non-repainting behavior - the structure level isn't knowable until confirmed."""
    n = len(bars15)
    confirmed = []
    for i in range(length, n - length):
        window = bars15[i - length:i + length + 1]
        h = bars15[i]["high"]
        l = bars15[i]["low"]
        ph = h if h == max(b["high"] for b in window) else None
        pl = l if l == min(b["low"] for b in window) else None
        if ph is not None or pl is not None:
            onset_index = i + length
            if onset_index < n:
                confirmed.append((bars15[onset_index]["time"], ph, pl))
    confirmed.sort(key=lambda x: x[0])
    return confirmed


def detect_choch_signals_dual_tf(bars15, bars1):
    """Structure from 15M pivots, CHoCH break checked on 1-minute closes -
    matches the live indicator's 'CONFIRMATION (1M)' mode exactly."""
    if len(bars15) < (SWING_LEN * 2 + 2) or len(bars1) < ATR_LEN + 2:
        return []

    pivot_events = find_pivots_15m(bars15, SWING_LEN)
    atr1 = compute_atr(bars1, ATR_LEN)

    struct_high = None
    struct_low = None
    trend = 0
    signals = []
    pivot_idx = 0
    n_pivots = len(pivot_events)

    for i in range(1, len(bars1)):
        t = bars1[i]["time"]
        while pivot_idx < n_pivots and pivot_events[pivot_idx][0] <= t:
            _, ph, pl = pivot_events[pivot_idx]
            if ph is not None:
                struct_high = ph
            if pl is not None:
                struct_low = pl
            pivot_idx += 1

        if atr1[i] is None or struct_high is None or struct_low is None:
            continue

        close = bars1[i]["close"]
        prev_close = bars1[i - 1]["close"]

        bullish_choch = (trend != 1) and (prev_close <= struct_high) and (close > struct_high)
        bearish_choch = (trend != -1) and (prev_close >= struct_low) and (close < struct_low)

        if bullish_choch:
            trend = 1
            entry = close
            sl = struct_low - atr1[i] * SL_BUFFER_MULT
            risk = abs(entry - sl)
            signals.append({"time_unix": t, "signal": "BUY", "entry": entry, "sl": sl,
                             "tp1": entry + risk * RR[0], "tp2": entry + risk * RR[1], "tp3": entry + risk * RR[2]})
        elif bearish_choch:
            trend = -1
            entry = close
            sl = struct_high + atr1[i] * SL_BUFFER_MULT
            risk = abs(entry - sl)
            signals.append({"time_unix": t, "signal": "SELL", "entry": entry, "sl": sl,
                             "tp1": entry - risk * RR[0], "tp2": entry - risk * RR[1], "tp3": entry - risk * RR[2]})

    return signals


@app.route("/backfill-historical", methods=["GET"])
def backfill_historical():
    bars15 = fetch_ohlc(interval="15min", outputsize=700)
    bars1 = fetch_ohlc(interval="1min", outputsize=5000)
    if not bars15 or not bars1:
        return json.dumps({"error": "Could not fetch price history (check TWELVE_DATA_KEY)"}), 500

    detected = detect_choch_signals_dual_tf(bars15, bars1)
    if not detected:
        return json.dumps({"detected": 0, "added": 0, "message": "No CHoCH setups found in the fetched history window"})

    history, sha = gh_load_history()
    existing_times = set(h.get("time_unix") for h in history if h.get("time_unix"))

    added = 0
    for s in detected:
        if s["time_unix"] in existing_times:
            continue
        dt_str = datetime.utcfromtimestamp(s["time_unix"]).strftime("%d %b %Y, %H:%M UTC")
        history.append({
            "symbol": "XAUUSD", "signal": s["signal"], "kind": "signal",
            "entry": f'{s["entry"]:.2f}', "sl": f'{s["sl"]:.2f}',
            "tp1": f'{s["tp1"]:.2f}', "tp2": f'{s["tp2"]:.2f}', "tp3": f'{s["tp3"]:.2f}',
            "chart_url": "", "time": dt_str, "time_unix": s["time_unix"]
        })
        added += 1

    history.sort(key=lambda x: x.get("time_unix", 0), reverse=True)
    history = history[:MAX_HISTORY]
    ok = gh_save_history(history, sha)
    if not ok:
        return json.dumps({"error": "Detected signals but GitHub save failed - check /debug-github"}), 500

    return json.dumps({
        "detected": len(detected), "added": added, "already_present": len(detected) - added,
        "bars_used": {"15min": len(bars15), "1min": len(bars1)}
    })


@app.route("/add-manual-signal", methods=["POST"])
def add_manual_signal():
    data = request.get_json(silent=True)
    if not data:
        return json.dumps({"error": "No data received"}), 400
    required = ["symbol", "signal", "entry", "sl", "tp1", "datetime"]
    for f in required:
        if not data.get(f):
            return json.dumps({"error": "Missing field: " + f}), 400
    try:
        import time as _time
        dt = datetime.strptime(data["datetime"], "%Y-%m-%dT%H:%M")
        time_unix = int(dt.timestamp())
        time_str = dt.strftime("%d %b %Y, %H:%M")
    except Exception as e:
        return json.dumps({"error": "Bad date/time: " + str(e)}), 400

    new_entry = {
        "symbol": data["symbol"], "signal": data["signal"], "kind": "signal",
        "entry": str(data["entry"]), "sl": str(data["sl"]),
        "tp1": str(data["tp1"]), "tp2": str(data.get("tp2") or ""), "tp3": str(data.get("tp3") or ""),
        "chart_url": "", "time": time_str, "time_unix": time_unix
    }
    try:
        history, sha = gh_load_history()
        history.insert(0, new_entry)
        history.sort(key=lambda x: x.get("time_unix", 0), reverse=True)
        history = history[:MAX_HISTORY]
        ok = gh_save_history(history, sha)
        if not ok:
            return json.dumps({"error": "GitHub save failed - check /debug-github"}), 500
    except Exception as e:
        return json.dumps({"error": "Save error: " + str(e)}), 500

    return json.dumps({"success": True}), 200


@app.route("/debug-github", methods=["GET"])
def debug_github():
    result = {
        "github_token_present": bool(GITHUB_TOKEN),
        "github_repo_value": GITHUB_REPO,
    }
    if not GITHUB_TOKEN or not GITHUB_REPO:
        result["problem"] = "GITHUB_TOKEN or GITHUB_REPO is missing/empty on the server."
        return Response(json.dumps(result, indent=2), mimetype="application/json")

    url = "https://api.github.com/repos/" + GITHUB_REPO + "/contents/" + HISTORY_PATH
    try:
        r = requests.get(url, headers=gh_headers(), timeout=15)
        result["get_status_code"] = r.status_code
        if r.status_code == 200:
            j = r.json()
            result["file_found"] = True
            result["sha"] = j.get("sha")
            try:
                content = base64.b64decode(j["content"]).decode("utf-8")
                parsed = json.loads(content)
                result["current_entry_count"] = len(parsed)
            except Exception as e:
                result["content_parse_error"] = str(e)
        else:
            result["file_found"] = False
            result["github_api_response"] = r.text[:500]
    except Exception as e:
        result["request_exception"] = str(e)

    return Response(json.dumps(result, indent=2), mimetype="application/json")


TWELVE_DATA_CRYPTO_MAP = {
    "BTC/USD": "BTC", "ETH/USD": "ETH", "BNB/USD": "BNB", "XRP/USD": "XRP", "SOL/USD": "SOL",
}
COINGECKO_ID_MAP = {
    "BTCUSDT": ("bitcoin", "BTC"), "ETHUSDT": ("ethereum", "ETH"), "BNBUSDT": ("binancecoin", "BNB"),
    "XRPUSDT": ("ripple", "XRP"), "SOLUSDT": ("solana", "SOL"), "TRXUSDT": ("tron", "TRX"),
    "HYPEUSDT": ("hyperliquid", "HYPE"), "DOGEUSDT": ("dogecoin", "DOGE"), "ZECUSDT": ("zcash", "ZEC"),
}
TOP_GAINERS_COUNT = 8
MIN_MARKET_CAP_USD = 20_000_000  # filters out illiquid/low-cap noise from top gainers

_crypto_cache = {"data": None, "ts": 0}
CRYPTO_CACHE_TTL = 1800  # 30 min - crypto is a bonus feature; gold price reliability takes priority


def fetch_main_coins_via_twelvedata():
    # Per-symbol calls, each isolated - one bad/unsupported symbol can't silently take
    # down the others. Cached for 10 min, and spaced slightly, so this burst of calls
    # never competes hard with the gold price fetching that shares the same API key/quota.
    import time as _time
    if not TWELVE_DATA_KEY:
        return []
    results = []
    for i, (td_symbol, label) in enumerate(TWELVE_DATA_CRYPTO_MAP.items()):
        if i > 0:
            _time.sleep(0.12)
        try:
            r = requests.get("https://api.twelvedata.com/quote",
                              params={"symbol": td_symbol, "apikey": TWELVE_DATA_KEY}, timeout=15)
            d = r.json()
            if "close" not in d or "percent_change" not in d:
                print("Twelve Data crypto quote missing fields for", td_symbol, ":", d)
                continue
            results.append({
                "symbol": label, "price": float(d["close"]),
                "change_pct": float(d["percent_change"]), "type": "main"
            })
        except Exception as e:
            print("Twelve Data crypto quote failed for", td_symbol, ":", repr(e))
            continue
    return results


def _fetch_coingecko_markets(**params):
    base = {"vs_currency": "usd", "price_change_percentage": "24h"}
    base.update(params)
    r = requests.get("https://api.coingecko.com/api/v3/coins/markets", params=base, timeout=15)
    r.raise_for_status()
    return r.json()


@app.route("/debug-crypto", methods=["GET"])
def debug_crypto():
    result = {}
    try:
        main_coins = fetch_main_coins_via_twelvedata()
        result["twelvedata_main_coins_success"] = len(main_coins) > 0
        result["twelvedata_coins_returned"] = [c["symbol"] for c in main_coins]
        result["twelvedata_coins_missing"] = [
            label for td_symbol, label in TWELVE_DATA_CRYPTO_MAP.items()
            if label not in [c["symbol"] for c in main_coins]
        ]
        result["twelvedata_sample"] = main_coins[0] if main_coins else None
    except Exception as e:
        result["twelvedata_main_coins_success"] = False
        result["twelvedata_error"] = repr(e)
    try:
        top_data = _fetch_coingecko_markets(order="market_cap_desc", per_page=10, page=1)
        result["coingecko_gainers_success"] = True
        result["coingecko_sample_count"] = len(top_data)
    except Exception as e:
        result["coingecko_gainers_success"] = False
        result["coingecko_error"] = repr(e)
    return Response(json.dumps(result, indent=2, default=str), mimetype="application/json")


FOREX_MAJOR_PAIRS = ["EUR/USD", "USD/JPY", "GBP/USD", "USD/CHF", "AUD/USD", "USD/CAD", "NZD/USD"]
_forex_ticker_cache = {"data": None, "ts": 0}
FOREX_TICKER_CACHE_TTL = 3600  # 1 hour - forex ticker is a bonus display, not a trading signal;
                                 # keeps worst-case usage around 168 credits/day (7 pairs x 24 refreshes)


def fetch_forex_ticker_via_twelvedata():
    import time as _time
    if not TWELVE_DATA_KEY:
        return []
    results = []
    for i, pair in enumerate(FOREX_MAJOR_PAIRS):
        if i > 0:
            _time.sleep(0.12)
        try:
            r = requests.get("https://api.twelvedata.com/quote",
                              params={"symbol": pair, "apikey": TWELVE_DATA_KEY}, timeout=15)
            d = r.json()
            if "close" not in d or "percent_change" not in d:
                print("Twelve Data forex quote missing fields for", pair, ":", d)
                continue
            results.append({
                "symbol": pair, "price": float(d["close"]),
                "change_pct": float(d["percent_change"]), "type": "forex"
            })
        except Exception as e:
            print("Twelve Data forex quote failed for", pair, ":", repr(e))
            continue
    return results


@app.route("/forex-ticker", methods=["GET"])
def forex_ticker():
    import time as _time
    now = _time.time()
    if _forex_ticker_cache["data"] is not None and (now - _forex_ticker_cache["ts"]) < FOREX_TICKER_CACHE_TTL:
        return Response(json.dumps({"pairs": _forex_ticker_cache["data"]}), mimetype="application/json")
    results = fetch_forex_ticker_via_twelvedata()
    if results:
        _forex_ticker_cache["data"] = results
        _forex_ticker_cache["ts"] = now
        return Response(json.dumps({"pairs": results}), mimetype="application/json")
    if _forex_ticker_cache["data"] is not None:
        return Response(json.dumps({"pairs": _forex_ticker_cache["data"], "stale": True}), mimetype="application/json")
    return Response(json.dumps({"pairs": []}), mimetype="application/json")


@app.route("/crypto-ticker", methods=["GET"])
def crypto_ticker():
    import time as _time
    now = _time.time()
    if _crypto_cache["data"] is not None and (now - _crypto_cache["ts"]) < CRYPTO_CACHE_TTL:
        return Response(json.dumps({"coins": _crypto_cache["data"]}), mimetype="application/json")

    results = []
    try:
        results.extend(fetch_main_coins_via_twelvedata())
    except Exception as e:
        print("Crypto ticker main-coins (Twelve Data) fetch failed:", repr(e))

    try:
        top_data = _fetch_coingecko_markets(order="market_cap_desc", per_page=250, page=1)
        main_gecko_ids = set(v[0] for v in COINGECKO_ID_MAP.values())
        gainer_candidates = [
            d for d in top_data
            if d["id"] not in main_gecko_ids
            and d.get("price_change_percentage_24h") is not None
            and d.get("market_cap") and d["market_cap"] >= MIN_MARKET_CAP_USD
            and d["price_change_percentage_24h"] > 0
        ]
        gainer_candidates.sort(key=lambda d: d["price_change_percentage_24h"], reverse=True)
        for d in gainer_candidates[:TOP_GAINERS_COUNT]:
            results.append({
                "symbol": d["symbol"].upper(), "price": float(d["current_price"]),
                "change_pct": float(d["price_change_percentage_24h"]), "type": "gainer"
            })
    except Exception as e:
        # Gainers are a bonus feature - main coins (Twelve Data) still work even if this fails
        print("Crypto ticker gainers (CoinGecko) fetch failed:", repr(e))

    if results:
        _crypto_cache["data"] = results
        _crypto_cache["ts"] = now
        return Response(json.dumps({"coins": results}), mimetype="application/json")

    # Any failure (rate limit, network issue, etc.) - serve the last successful
    # result regardless of how stale it is, rather than showing nothing.
    if _crypto_cache["data"] is not None:
        return Response(json.dumps({"coins": _crypto_cache["data"], "stale": True}), mimetype="application/json")
    return Response(json.dumps({"coins": []}), mimetype="application/json")



@app.route("/ping", methods=["GET"])
def ping():
    return "pong", 200


@app.route("/vapid-public-key", methods=["GET"])
def vapid_public_key():
    return Response(json.dumps({"key": VAPID_PUBLIC_KEY}), mimetype="application/json")


@app.route("/subscribe", methods=["POST"])
def subscribe():
    sub = request.get_json(silent=True)
    if not sub or "endpoint" not in sub:
        return "Invalid subscription", 400
    subs, sha = gh_load_json(SUBS_PATH)
    _kid = _current_key_id()
    if _kid:
        sub["_k"] = _kid
    if not any(s.get("endpoint") == sub.get("endpoint") for s in subs):
        subs.append(sub)
        gh_save_json(SUBS_PATH, subs, sha)
    return "OK", 200


@app.route("/debug-chart", methods=["GET"])
def debug_chart():
    result = {"twelve_data_key_present": bool(TWELVE_DATA_KEY)}
    if not TWELVE_DATA_KEY:
        result["problem"] = "TWELVE_DATA_KEY missing on the server."
        return Response(json.dumps(result, indent=2), mimetype="application/json")
    try:
        closes = fetch_closes()
        result["closes_fetched"] = len(closes) if closes else 0
        if not closes or len(closes) <= 10:
            result["problem"] = "Not enough price data returned from Twelve Data"
            return Response(json.dumps(result, indent=2), mimetype="application/json")
        config = build_chart_config(closes, 4655.07, 4681.79, 4626.35, 4601.64, 4574.92, "SELL")
        png_bytes = render_chart_png_bytes(config)
        result["chart_render_success"] = True
        result["chart_bytes"] = len(png_bytes)
    except Exception as e:
        result["chart_render_success"] = False
        result["error"] = repr(e)
    return Response(json.dumps(result, indent=2), mimetype="application/json")


@app.route("/chart-image", methods=["GET"])
def chart_image():
    try:
        entry = float(request.args.get("entry"))
        sl = float(request.args.get("sl"))
        tp1 = float(request.args.get("tp1"))
        tp2 = float(request.args.get("tp2", tp1))
        tp3 = float(request.args.get("tp3", tp1))
        signal = request.args.get("signal", "BUY")
    except (TypeError, ValueError):
        return "Bad or missing parameters", 400

    closes = fetch_closes()
    if not closes or len(closes) <= 10:
        return "Could not fetch price data", 502
    try:
        config = build_chart_config(closes, entry, sl, tp1, tp2, tp3, signal)
        png_bytes = render_chart_png_bytes(config)
    except Exception as e:
        return "Chart render failed: " + str(e), 502
    return Response(png_bytes, mimetype="image/png")


@app.route("/candles", methods=["GET"])
def candles():
    bars = fetch_ohlc(outputsize=300)
    if bars is None:
        return Response(json.dumps({"bars": []}), mimetype="application/json")
    return Response(json.dumps({"bars": bars}), mimetype="application/json")


_ind_raw = {"ts": 0, "b15": None, "b1": None}


def _ind_store(b15, b1):
    _ind_raw["ts"] = _time_mod.time()
    _ind_raw["b15"] = b15
    _ind_raw["b1"] = b1


def _agg(bars, period):
    out = []
    for b in bars:
        k = b["time"] - b["time"] % period
        if out and out[-1]["time"] == k:
            o = out[-1]
            o["high"] = max(o["high"], b["high"])
            o["low"] = min(o["low"], b["low"])
            o["close"] = b["close"]
        else:
            out.append({"time": k, "open": b["open"], "high": b["high"], "low": b["low"], "close": b["close"]})
    return out


def _ev_dict(e):
    return {"signal": e["signal"], "kind": e["kind"], "time_unix": e["time_unix"],
            "entry": round(e["entry"], 2), "sl": round(e["sl"], 2),
            "tp1": round(e["tp1"], 2), "tp2": round(e["tp2"], 2), "tp3": round(e["tp3"], 2)}


def _setup_status(ev, bars1):
    sign = 1 if ev["signal"] == "BUY" else -1
    best = 0
    for b in bars1:
        if b["time"] <= ev["time_unix"]:
            continue
        hit_sl = (b["low"] <= ev["sl"]) if sign == 1 else (b["high"] >= ev["sl"])
        if hit_sl:
            return "Stopped out (SL hit)" if best == 0 else "TP%d hit" % best
        for n, key in ((3, "tp3"), (2, "tp2"), (1, "tp1")):
            reached = (b["high"] >= ev[key]) if sign == 1 else (b["low"] <= ev[key])
            if reached:
                best = max(best, n)
                break
        if best == 3:
            return "TP3 hit"
    return ("TP%d hit" % best) if best else "Active"


@app.route("/indicator-data", methods=["GET"])
def indicator_data():
    age = _time_mod.time() - _ind_raw["ts"]
    if _ind_raw["b15"] is None or (age > 420 and not market_is_closed()):
        nb15 = fetch_ohlc(interval="15min", outputsize=300)
        nb1 = fetch_ohlc(interval="1min", outputsize=1500)
        if nb15 and nb1:
            _ind_store(nb15, nb1)
        elif _ind_raw["b15"] is None:
            return Response(json.dumps({"error": "Could not fetch candles"}), status=502, mimetype="application/json")
    bars15, bars1 = _ind_raw["b15"], _ind_raw["b1"]
    det15 = drop_unfinished_bar(bars15, 900)
    det1 = drop_unfinished_bar(bars1, 60)
    events = detect_events_dual_tf(det15, det1)
    period = {"1": 60, "5": 300, "15": 900, "60": 3600, "240": 14400}.get(request.args.get("tf", "15"), 900)
    if period == 60:
        disp = bars1
    elif period == 300:
        disp = _agg(bars1, 300)
    elif period == 900:
        disp = bars15
    else:
        disp = _agg(bars15, period)
    t0 = disp[0]["time"]
    pivots = find_pivots_15m(det15, SWING_LEN)

    def level_series(idx):
        pts = []
        carry = None
        for t, ph, pl in pivots:
            v = (ph, pl)[idx]
            if v is None:
                continue
            st = t - t % period
            if st < t0:
                carry = v
            elif pts and pts[-1]["time"] == st:
                pts[-1]["value"] = v
            else:
                pts.append({"time": st, "value": v})
        if carry is not None and (not pts or pts[0]["time"] > t0):
            pts.insert(0, {"time": t0, "value": carry})
        if pts and pts[-1]["time"] < disp[-1]["time"]:
            pts.append({"time": disp[-1]["time"], "value": pts[-1]["value"]})
        return pts

    sigs = [e for e in events if e["kind"] == "signal"]
    latest = None
    if sigs:
        latest = _ev_dict(sigs[-1])
        latest["status"] = _setup_status(sigs[-1], det1)
        latest["risk_pips"] = round(abs(sigs[-1]["entry"] - sigs[-1]["sl"]) / GOLD_PIP, 1)
    body = {
        "bars": disp,
        "period": period,
        "struct_high": level_series(0),
        "struct_low": level_series(1),
        "events": [_ev_dict(e) for e in events if e["time_unix"] >= t0],
        "latest": latest,
        "price": bars1[-1]["close"],
        "last_candle": bars1[-1]["time"],
        "updated": int(_ind_raw["ts"]),
        "market_closed": market_is_closed(),
        "levels": _levels(bars15),
    }
    return Response(json.dumps(body), mimetype="application/json")


GOLD_PIP = 0.1   # 1 pip = $0.10 price move on gold (10 pips = $1.00)
_res_cache = {"ts": 0, "trades": None, "untracked": 0, "price": None, "error": None}
_res_closed = {}
_lp_cache = {"ts": 0, "price": None, "src": None}


def _is_real_signal(s):
    if s.get("kind") != "signal" or "time_unix" not in s:
        return False
    try:
        for k in ("entry", "sl", "tp1", "tp2", "tp3"):
            float(s[k])
    except Exception:
        return False
    if str(s.get("entry")) == "4000.00" and str(s.get("sl")) == "3990.00":
        return False  # dummy test alert
    return True


def _sig_key(s):
    return "%s|%s|%s" % (s.get("time_unix"), s.get("signal"), s.get("entry"))


def _trade_outcome(s, b1, b15):
    sign = 1 if s["signal"] == "BUY" else -1
    entry, sl = float(s["entry"]), float(s["sl"])
    tps = [float(s["tp1"]), float(s["tp2"]), float(s["tp3"])]
    t = int(s["time_unix"])
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    if b1 and b1[0]["time"] <= t:
        bars = [b for b in b1 if b["time"] > t]
        src = "1m"
    elif b15 and b15[0]["time"] <= t:
        nxt = t - t % 900 + 900
        bars = [b for b in b15 if b["time"] >= nxt]
        src = "15m"
    else:
        return None
    tp_hit = 0
    sl_hit = False
    mfe = 0.0
    mae = 0.0
    for b in bars:
        fav = (b["high"] - entry) if sign == 1 else (entry - b["low"])
        adv = (entry - b["low"]) if sign == 1 else (b["high"] - entry)
        sl_touch = (b["low"] <= sl) if sign == 1 else (b["high"] >= sl)
        mae = max(mae, adv)
        if sl_touch:
            sl_hit = True  # conservative: if a candle touches SL and a target, SL counts first
            break
        mfe = max(mfe, fav)
        for n in (1, 2, 3):
            hit = (b["high"] >= tps[n - 1]) if sign == 1 else (b["low"] <= tps[n - 1])
            if hit and n > tp_hit:
                tp_hit = n
        if tp_hit == 3:
            break
    risk_pips = risk / GOLD_PIP
    booked_r = sum(range(1, tp_hit + 1)) / 3.0   # one third closed at each target reached (1R, 2R, 3R)
    status = "sl" if sl_hit else ("tp3" if tp_hit == 3 else "open")
    r = booked_r - (3 - tp_hit) / 3.0 if sl_hit else booked_r
    last = bars[-1]["close"] if bars else entry
    float_r = 0.0
    if status == "open":
        float_r = ((last - entry) * sign / risk) * (3 - tp_hit) / 3.0
    return {"status": status, "tp_hit": tp_hit, "r": round(r, 3), "pips": round(r * risk_pips, 1),
            "float_pips": round(float_r * risk_pips, 1), "risk_pips": round(risk_pips, 1),
            "mfe_pips": round(mfe / GOLD_PIP, 1), "mae_pips": round(mae / GOLD_PIP, 1), "src": src}


def _compute_results(force=False):
    now = _time_mod.time()
    if _res_cache["trades"] is not None and now - _res_cache["ts"] < (60 if force else 300):
        return _res_cache
    history, _ = gh_load_history()
    sigs = [s for s in history if _is_real_signal(s)]
    try:
        # indicator setups from the last day that were never alerted (e.g. server was paused): include them so results match the chart
        r1, r15 = _ind_raw["b1"], _ind_raw["b15"]
        if r1 and r15:
            for ev in detect_events_dual_tf(drop_unfinished_bar(r15, 900), drop_unfinished_bar(r1, 60)):
                if ev["kind"] != "signal":
                    continue
                if any(h.get("signal") == ev["signal"] and abs(int(h.get("time_unix", 0) or 0) - ev["time_unix"]) <= 300 for h in history):
                    continue
                f2 = lambda v: "%.2f" % v
                sigs.append({"signal": ev["signal"], "kind": "signal", "entry": f2(ev["entry"]), "sl": f2(ev["sl"]),
                             "tp1": f2(ev["tp1"]), "tp2": f2(ev["tp2"]), "tp3": f2(ev["tp3"]), "time_unix": ev["time_unix"],
                             "time": datetime.utcfromtimestamp(ev["time_unix"]).strftime("%d %b %Y, %H:%M UTC")})
    except Exception as e:
        print("results: chart-signal merge failed:", repr(e))
    todo = [s for s in sigs if _sig_key(s) not in _res_closed]
    b1 = b15 = None
    if todo:
        oldest = min(int(s["time_unix"]) for s in todo)
        raw1, raw15 = _ind_raw["b1"], _ind_raw["b15"]
        if raw1 and raw1[0]["time"] <= oldest and (now - _ind_raw["ts"] < 420 or market_is_closed()):
            b1, b15 = raw1, raw15
        else:
            b15 = fetch_ohlc(interval="15min", outputsize=5000)
            b1 = fetch_ohlc(interval="1min", outputsize=5000)
            if not b15 and not b1:
                b1, b15 = raw1, raw15
            if not b15 and not b1:
                _res_cache["error"] = "Could not fetch price history"
                if _res_cache["trades"] is not None:
                    return _res_cache
    trades = []
    untracked = 0
    for s in sigs:
        key = _sig_key(s)
        o = _res_closed.get(key)
        if o is None:
            o = _trade_outcome(s, b1, b15)
            if o is not None and o["status"] != "open":
                _res_closed[key] = o
        if o is None:
            untracked += 1
            continue
        t = {"time_unix": int(s["time_unix"]), "time": s.get("time", ""), "signal": s["signal"],
             "entry": float(s["entry"]), "sl": float(s["sl"]), "tp1": float(s["tp1"]),
             "tp2": float(s["tp2"]), "tp3": float(s["tp3"])}
        t.update(o)
        trades.append(t)
    trades.sort(key=lambda x: x["time_unix"], reverse=True)
    price = None
    src = b1 or b15 or _ind_raw["b1"] or _ind_raw["b15"]
    if src:
        price = src[-1]["close"]
    _res_cache.update({"ts": now, "trades": trades, "untracked": untracked, "price": price, "error": None})
    return _res_cache


@app.route("/results", methods=["GET"])
def results_endpoint():
    c = _compute_results(force=request.args.get("refresh") == "1")
    return Response(json.dumps({
        "trades": c["trades"] or [], "untracked": c["untracked"], "price": c["price"],
        "updated": int(c["ts"]), "pip": GOLD_PIP, "error": c["error"]
    }), mimetype="application/json")


@app.route("/live-price", methods=["GET"])
def live_price():
    now = _time_mod.time()
    if _lp_cache["price"] is not None and now - _lp_cache["ts"] < 45:
        return Response(json.dumps(_lp_cache), mimetype="application/json")
    price, src = None, None
    if TWELVE_DATA_KEY and not market_is_closed():
        try:
            r = requests.get("https://api.twelvedata.com/price",
                             params={"symbol": "XAU/USD", "apikey": TWELVE_DATA_KEY}, timeout=8)
            price = float(r.json()["price"])
            src = "live"
        except Exception as e:
            print("live-price failed:", repr(e))
    if price is None:
        raw = _ind_raw["b1"] or _ind_raw["b15"]
        if raw:
            price, src = raw[-1]["close"], "candle"
    if price is None:
        return Response(json.dumps({"price": None}), mimetype="application/json")
    _lp_cache.update({"ts": now, "price": price, "src": src})
    return Response(json.dumps(_lp_cache), mimetype="application/json")


def _levels(bars15):
    if not bars15:
        return None
    day0 = bars15[-1]["time"] - bars15[-1]["time"] % 86400

    def span(a, b):
        return [x for x in bars15 if a <= x["time"] < b]

    today = span(day0, day0 + 86400)
    prev = []
    d = day0
    for _ in range(5):
        d -= 86400
        prev = span(d, d + 86400)
        if len(prev) >= 8:
            break
    out = {}
    if today:
        dh = max(x["high"] for x in today)
        dl = min(x["low"] for x in today)
        out.update({"day_open": today[0]["open"], "day_high": dh, "day_low": dl,
                    "range_pips": round((dh - dl) / GOLD_PIP)})
    if len(prev) >= 8:
        ph = max(x["high"] for x in prev)
        pl = min(x["low"] for x in prev)
        out.update({"pdh": ph, "pdl": pl, "pdc": prev[-1]["close"], "prev_range_pips": round((ph - pl) / GOLD_PIP)})
    h1 = _agg(bars15, 3600)
    atr = [v for v in compute_atr(h1, 14) if v is not None]
    if atr:
        out["atr_pips"] = round(atr[-1] / GOLD_PIP)
    return out


@app.route("/stats7d", methods=["GET"])
def stats7d():
    return Response(json.dumps(get_7day_stats()), mimetype="application/json")


# =============================================================
# ACCESS KEYS (paid access): set ADMIN_KEY in Render to switch on
# ================================================================
import secrets as _sec
import hmac as _hm
import hashlib as _hl
import time as _tm
from datetime import timedelta as _td

ADMIN_KEY = os.environ.get("ADMIN_KEY", "")
KEYS_PATH = "data/keys.json"
_kc = {"ts": 0, "list": []}
_fails = {}
_OPEN_PATHS = {"/", "/ping", "/manifest.json", "/sw.js", "/vapid-public-key", "/scan-signals",
               "/check-forex-news", "/webhook", "/auth", "/auth-status"}


def _eq(a, b):
    if not a or not b:
        return False
    return _hm.compare_digest(str(a).encode(), str(b).encode())


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _key_active(rec):
    if not rec or rec.get("revoked"):
        return False
    exp = rec.get("expires")
    return (not exp) or _today() <= exp


def _keys():
    if _tm.time() - _kc["ts"] > 90:
        lst, sha = gh_load_json(KEYS_PATH)
        if sha is not None and isinstance(lst, list):
            _kc["list"] = lst
            _kc["ts"] = _tm.time()
        elif not _kc["list"]:
            _kc["ts"] = _tm.time()
        else:
            _kc["ts"] = _tm.time() - 60  # GitHub hiccup: keep old keys, retry in 30s
    return _kc["list"]


def _keys_write(mutator):
    lst, sha = gh_load_json(KEYS_PATH)
    if sha is None and _kc["list"]:
        return False, None
    result = mutator(lst)
    if gh_save_json(KEYS_PATH, lst, sha):
        _kc["list"] = lst
        _kc["ts"] = _tm.time()
        return True, result
    return False, None


def _find_by_value(val):
    v = (val or "").strip().upper()
    for r in _keys():
        if _eq(r.get("key"), v):
            return r
    return None


def _find_by_id(kid):
    for r in _keys():
        if r.get("id") == kid:
            return r
    return None


def _client_ip():
    return (request.headers.get("X-Forwarded-For", request.remote_addr or "") or "").split(",")[0].strip()


def _rate_blocked():
    ip = _client_ip()
    now = _tm.time()
    arr = [t for t in _fails.get(ip, []) if now - t < 600]
    _fails[ip] = arr
    return len(arr) >= 8


def _rate_fail():
    _fails.setdefault(_client_ip(), []).append(_tm.time())


def _access():
    k = request.cookies.get("gk", "")
    if not k:
        return False, None
    if ADMIN_KEY and _eq(k, ADMIN_KEY):
        return True, {"id": "owner", "label": "Owner", "expires": None}
    rec = _find_by_value(k)
    if not rec or not _key_active(rec):
        return False, None
    d = request.cookies.get("gd", "")
    if not d or d not in rec.get("devices", []):
        return False, None
    return True, rec


def _current_key_id():
    if not ADMIN_KEY:
        return None
    ok, rec = _access()
    return rec["id"] if ok else None


def _push_allowed(sub):
    if not ADMIN_KEY:
        return True
    kid = sub.get("_k")
    if not kid or kid == "owner":
        return True
    return _key_active(_find_by_id(kid))


def _json(obj, status=200):
    return Response(json.dumps(obj), status=status, mimetype="application/json")


@app.before_request
def _gate():
    if not ADMIN_KEY:
        return None
    p = request.path
    if p in _OPEN_PATHS or p.startswith("/admin") or p.endswith((".png", ".ico")):
        return None
    ok, _ = _access()
    if ok:
        return None
    return _json({"error": "locked"}, 401)


@app.route("/auth-status", methods=["GET"])
def auth_status():
    if not ADMIN_KEY:
        return _json({"gated": False, "ok": True})
    ok, rec = _access()
    return _json({"gated": True, "ok": ok, "label": rec.get("label") if rec else None,
                  "expires": rec.get("expires") if rec else None})


@app.route("/auth", methods=["POST"])
def auth():
    if not ADMIN_KEY:
        return _json({"ok": True})
    if _rate_blocked():
        return _json({"error": "Too many attempts. Try again in 10 minutes."}, 429)
    data = request.get_json(silent=True) or {}
    key = (data.get("key") or "").strip()
    resp_ok = {"ok": True}
    if _eq(key, ADMIN_KEY):
        resp = _json(resp_ok)
        resp.set_cookie("gk", key, max_age=34000000, httponly=True, secure=True, samesite="Lax")
        return resp
    rec = _find_by_value(key)
    if not rec or not _key_active(rec):
        _rate_fail()
        return _json({"error": "Invalid or expired key"}, 401)
    gd = request.cookies.get("gd", "") or _sec.token_hex(12)
    devices = rec.get("devices", [])
    if gd not in devices:
        if len(devices) >= int(rec.get("max_devices", 2)):
            return _json({"error": "Device limit reached for this key. Contact the seller."}, 403)

        def add(lst):
            for r in lst:
                if r.get("id") == rec["id"]:
                    r.setdefault("devices", [])
                    if gd not in r["devices"]:
                        r["devices"].append(gd)
            return True
        okw, _r = _keys_write(add)
        if not okw:
            return _json({"error": "Server busy, try again in a minute."}, 503)
    resp = _json(resp_ok)
    resp.set_cookie("gk", rec["key"], max_age=34000000, httponly=True, secure=True, samesite="Lax")
    resp.set_cookie("gd", gd, max_age=34000000, httponly=True, secure=True, samesite="Lax")
    return resp


# ---------------- admin ----------------
def _admin_token():
    return _hm.new(ADMIN_KEY.encode(), b"admin-session", _hl.sha256).hexdigest()


def _is_admin():
    return bool(ADMIN_KEY) and _eq(request.cookies.get("ga", ""), _admin_token())


@app.route("/admin/login", methods=["POST"])
def admin_login():
    if not ADMIN_KEY:
        return _json({"error": "ADMIN_KEY is not set on the server"}, 503)
    if _rate_blocked():
        return _json({"error": "Too many attempts. Try again later."}, 429)
    data = request.get_json(silent=True) or {}
    if not _eq((data.get("key") or "").strip(), ADMIN_KEY):
        _rate_fail()
        return _json({"error": "Wrong admin key"}, 401)
    resp = _json({"ok": True})
    resp.set_cookie("ga", _admin_token(), max_age=2592000, httponly=True, secure=True, samesite="Strict")
    return resp


def _pub(r):
    return {"id": r.get("id"), "label": r.get("label"), "key": r.get("key"), "created": r.get("created"),
            "expires": r.get("expires"), "max_devices": r.get("max_devices", 2),
            "devices": len(r.get("devices", [])), "revoked": bool(r.get("revoked")),
            "active": _key_active(r)}


@app.route("/admin/api/list", methods=["GET"])
def admin_list():
    if not _is_admin():
        return _json({"error": "auth"}, 401)
    _kc["ts"] = 0
    return _json({"keys": [_pub(r) for r in _keys()], "today": _today()})


@app.route("/admin/api/create", methods=["POST"])
def admin_create():
    if not _is_admin():
        return _json({"error": "auth"}, 401)
    d = request.get_json(silent=True) or {}
    label = (str(d.get("label") or "Customer"))[:60]
    try:
        days = int(d.get("days") or 0)
    except Exception:
        days = 0
    try:
        maxd = max(1, min(10, int(d.get("max_devices") or 2)))
    except Exception:
        maxd = 2
    alpha = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    key = "GS-" + "-".join("".join(_sec.choice(alpha) for _ in range(4)) for _ in range(3))
    rec = {"id": _sec.token_hex(4), "label": label, "key": key, "created": _today(),
           "expires": (datetime.now(timezone.utc) + _td(days=days)).strftime("%Y-%m-%d") if days > 0 else None,
           "max_devices": maxd, "devices": [], "revoked": False}

    def add(lst):
        lst.append(rec)
        return True
    ok, _r = _keys_write(add)
    if not ok:
        return _json({"error": "Could not save to GitHub"}, 500)
    return _json({"ok": True, "key": _pub(rec)})


@app.route("/admin/api/update", methods=["POST"])
def admin_update():
    if not _is_admin():
        return _json({"error": "auth"}, 401)
    d = request.get_json(silent=True) or {}
    kid, act = d.get("id"), d.get("action")
    try:
        days = int(d.get("days") or 30)
    except Exception:
        days = 30

    def mut(lst):
        for i, r in enumerate(lst):
            if r.get("id") != kid:
                continue
            if act == "revoke":
                r["revoked"] = True
            elif act == "restore":
                r["revoked"] = False
            elif act == "reset":
                r["devices"] = []
            elif act == "devices":
                r["max_devices"] = max(1, min(10, days))
            elif act == "extend":
                base = max(r.get("expires") or _today(), _today())
                r["expires"] = (datetime.strptime(base, "%Y-%m-%d") + _td(days=days)).strftime("%Y-%m-%d")
            elif act == "delete":
                lst.pop(i)
            else:
                return False
            return True
        return False
    ok, found = _keys_write(mut)
    if not ok or not found:
        return _json({"error": "Update failed"}, 500)
    return _json({"ok": True})


@app.route("/admin", methods=["GET"])
def admin_page():
    return Response(ADMIN_HTML, mimetype="text/html")


ADMIN_HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>Access Admin</title><style>
:root{--bg:#0e0f12;--card:#181a20;--b:#2a2d36;--t:#f2f3f5;--m:#9aa0ab;--a:#f5b301;--g:#2bb673;--r:#e5484d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--t);font:15px/1.4 system-ui,sans-serif;padding:16px;max-width:640px;margin:auto}
h1{font-size:20px;margin:6px 0 14px}.card{background:var(--card);border:1px solid var(--b);border-radius:12px;padding:14px;margin-bottom:12px}
input{width:100%;background:#0e0f12;color:var(--t);border:1px solid var(--b);border-radius:8px;padding:10px;font-size:15px;margin:4px 0 8px}
.row{display:flex;gap:8px}.row>*{flex:1}label{font-size:12px;color:var(--m)}
button{background:var(--a);color:#111;border:0;border-radius:8px;padding:9px 12px;font-weight:700;font-size:13px;cursor:pointer}
button.s{background:#262932;color:var(--t);border:1px solid var(--b)}button.d{background:#3a1e20;color:#ff8a8f;border:1px solid #5a2a2d}
.k{font-family:ui-monospace,monospace;font-size:15px;letter-spacing:.5px;color:var(--a);cursor:pointer;word-break:break-all}
.tag{display:inline-block;font-size:11px;font-weight:700;border-radius:20px;padding:2px 9px}.on{background:#12351f;color:var(--g)}.off{background:#3a1e20;color:#ff8a8f}
.m{color:var(--m);font-size:12px;margin:2px 0 8px}.btns{display:flex;flex-wrap:wrap;gap:6px}#msg{color:var(--m);font-size:13px;min-height:18px}
</style></head><body><h1>Access keys</h1>
<div id="login" class="card" style="display:none"><label>Admin key</label><input id="ak" type="password" autocomplete="off">
<button onclick="login()">Sign in</button><div id="msg"></div></div>
<div id="main" style="display:none">
<div class="card"><b>New customer key</b><label>Customer name</label><input id="nl" placeholder="e.g. Rahul">
<div class="row"><div><label>Valid for (days, 0 = no expiry)</label><input id="nd" type="number" value="30"></div>
<div><label>Max devices</label><input id="nm" type="number" value="2"></div></div>
<button onclick="create()">Create key</button><div id="msg2"></div></div>
<div id="list"></div></div>
<script>
const $=id=>document.getElementById(id);
async function api(p,b){const r=await fetch(p,b?{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)}:{});let j={};try{j=await r.json()}catch(e){}return{s:r.status,j}}
async function login(){const r=await api("/admin/login",{key:$("ak").value});if(r.s==200){load()}else $("msg").textContent=r.j.error||"Failed"}
function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]))}
function invite(k){return "Bullion Radar access\nApp: "+location.origin+"/\nYour key: "+k.key+(k.expires?"\nValid till: "+k.expires:"")+"\nEnter the key when the app asks. Works on up to "+k.max_devices+" devices."}
async function load(){const r=await api("/admin/api/list");if(r.s!=200){$("login").style.display="block";$("main").style.display="none";return}
$("login").style.display="none";$("main").style.display="block";window._k=r.j.keys;
$("list").innerHTML=r.j.keys.length?r.j.keys.map((k,i)=>`<div class="card"><b>${esc(k.label)}</b> <span class="tag ${k.active?"on":"off"}">${k.revoked?"Revoked":k.active?"Active":"Expired"}</span>
<div class="k" onclick="copy(${i},0)">${esc(k.key)}</div>
<div class="m">Expires ${k.expires||"never"} · Devices ${k.devices}/${k.max_devices} · Created ${k.created}</div>
<div class="btns"><button onclick="copy(${i},1)">Copy invite</button><button class="s" onclick="act('${k.id}','extend',30)">+30 days</button>
${k.revoked?`<button class="s" onclick="act('${k.id}','restore')">Restore</button>`:`<button class="d" onclick="act('${k.id}','revoke')">Revoke</button>`}
<button class="s" onclick="act('${k.id}','reset')">Reset devices</button><button class="d" onclick="del('${k.id}')">Delete</button></div></div>`).join(""):'<div class="m">No keys yet.</div>'}
function copy(i,inv){const k=window._k[i];navigator.clipboard.writeText(inv?invite(k):k.key);$("msg2").textContent="Copied "+(inv?"invite message":"key")}
async function act(id,a,d){const r=await api("/admin/api/update",{id,action:a,days:d});$("msg2").textContent=r.s==200?"Done":(r.j.error||"Failed");load()}
async function del(id){if(confirm("Delete this key permanently?"))act(id,"delete")}
async function create(){const r=await api("/admin/api/create",{label:$("nl").value,days:$("nd").value,max_devices:$("nm").value});
if(r.s==200){$("nl").value="";$("msg2").textContent="Created "+r.j.key.key+" (tap it in the list to copy)"}else $("msg2").textContent=r.j.error||"Failed";load()}
load();
</script></body></html>"""




@app.route("/latest", methods=["GET"])
def latest():
    history, _ = gh_load_history()
    return Response(json.dumps({"signals": history}), mimetype="application/json")


@app.route("/webhook", methods=["POST"])
def webhook():
    # --- shared-secret check: set WEBHOOK_SECRET in Render; send it as ?token=..., header X-Webhook-Token, or "token" in the JSON body ---
    import hmac
    secret = os.environ.get("WEBHOOK_SECRET", "")
    if not secret:
        return "Webhook disabled: WEBHOOK_SECRET not configured", 503
    _body = request.get_json(silent=True)
    _given = (request.args.get("token") or request.headers.get("X-Webhook-Token")
              or (_body.get("token") if isinstance(_body, dict) else "") or "")
    if not hmac.compare_digest(str(_given).encode(), secret.encode()):
        return "Unauthorized", 401
    raw = request.get_data(as_text=True).strip()

    if not raw:
        return "Empty message", 400
    if not BOT_TOKEN or not CHAT_ID:
        print("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set.")
        return "Server config missing", 500

    payload = None
    try:
        payload = json.loads(raw)
    except Exception:
        payload = None

    if payload is None:
        r = send_text(raw)
        return ("OK", 200) if r.status_code == 200 else ("Telegram error", 500)

    symbol = payload.get("symbol", "XAUUSD")
    signal = payload.get("signal", "")
    kind = payload.get("kind", "signal")
    entry = payload.get("entry", "")
    sl = payload.get("sl", "")
    tp1 = payload.get("tp1", "")
    tp2 = payload.get("tp2", "")
    tp3 = payload.get("tp3", "")

    caption = build_caption(symbol, signal, kind, entry, sl, tp1, tp2, tp3)

    chart_sent = False
    chart_url_for_app = ""
    if TWELVE_DATA_KEY:
        try:
            closes = fetch_closes()
            if closes and len(closes) > 10:
                config = build_chart_config(closes, float(entry), float(sl), float(tp1), float(tp2), float(tp3), signal)
                png_bytes = render_chart_png_bytes(config)
                r = send_photo_bytes(png_bytes, caption)
                chart_sent = r.status_code == 200
                if not chart_sent:
                    print("Telegram photo send failed:", r.status_code, r.text[:300])
                chart_url_for_app = ("/chart-image?signal=" + signal + "&entry=" + str(entry) +
                                      "&sl=" + str(sl) + "&tp1=" + str(tp1) + "&tp2=" + str(tp2) + "&tp3=" + str(tp3))
        except Exception as e:
            print("Chart generation/send failed:", repr(e))

    if not chart_sent:
        send_text(caption)

    new_entry = {
        "symbol": symbol, "signal": signal, "kind": kind,
        "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3,
        "chart_url": chart_url_for_app,
        "time": datetime.utcnow().strftime("%d %b %Y, %H:%M UTC"),
        "time_unix": int(datetime.utcnow().timestamp())
    }

    try:
        history, sha = gh_load_history()
        history.insert(0, new_entry)
        history = history[:MAX_HISTORY]
        gh_save_history(history, sha)
    except Exception as e:
        print("GitHub history save failed:", e)

    try:
        push_dot = "🟢" if signal == "BUY" else "🔴"
        push_title = push_dot + " " + signal + (" Setup" if kind == "signal" else " Zone Touched Again")
        push_body = "Entry " + entry + " | SL " + sl + " | TP1 " + tp1
        send_push_to_all(push_title, push_body, "/")
    except Exception as e:
        print("Push notification failed:", e)

    return "OK", 200


# ======================================================================
# SERVER-SIDE SIGNAL SCANNER (replaces TradingView webhooks)
# cron-job.org calls /scan-signals every few minutes. The server pulls
# fresh 15M + 1M gold candles, runs the same CHoCH logic as the Pine
# indicator, and sends Telegram + push + app history for anything new.
# ======================================================================
import time as _time_mod

SCAN_RECENT_SIGNAL_SEC = 25 * 60   # only alert on setups formed in the last 25 min
SCAN_RECENT_TOUCH_SEC = 12 * 60    # zone re-touches: last 12 min only
ZONE_REARM_MULT = 0.15


def market_is_closed(now=None):
    """Gold (spot) is closed from Friday ~22:00 UTC to Sunday ~22:00 UTC."""
    now = now or datetime.utcnow()
    wd = now.weekday()  # Mon=0 ... Sun=6
    if wd == 5:
        return True
    if wd == 4 and now.hour >= 22:
        return True
    if wd == 6 and now.hour < 22:
        return True
    return False


def drop_unfinished_bar(bars, seconds):
    """Remove the still-forming last candle so signals fire on CLOSED candles only."""
    if not bars:
        return bars
    now_ts = _time_mod.time()
    if bars[-1]["time"] + seconds > now_ts:
        return bars[:-1]
    return bars


def detect_events_dual_tf(bars15, bars1):
    """Same as detect_choch_signals_dual_tf, plus the indicator's repeatable
    'zone re-touch' alerts. Returns a list of events sorted by time:
    {kind: 'signal'|'touch', signal, time_unix, entry, sl, tp1, tp2, tp3}"""
    if len(bars15) < (SWING_LEN * 2 + 2) or len(bars1) < ATR_LEN + 2:
        return []

    pivot_events = find_pivots_15m(bars15, SWING_LEN)
    atr1 = compute_atr(bars1, ATR_LEN)

    struct_high = None
    struct_low = None
    trend = 0
    pivot_idx = 0
    n_pivots = len(pivot_events)
    events = []

    cur = None  # current setup dict
    long_watch = short_watch = False
    away_buy = away_sell = True

    for i in range(1, len(bars1)):
        b = bars1[i]
        t = b["time"]
        while pivot_idx < n_pivots and pivot_events[pivot_idx][0] <= t:
            _, ph, pl = pivot_events[pivot_idx]
            if ph is not None:
                struct_high = ph
            if pl is not None:
                struct_low = pl
            pivot_idx += 1

        if atr1[i] is None or struct_high is None or struct_low is None:
            continue

        close = b["close"]
        prev_close = bars1[i - 1]["close"]
        atr = atr1[i]

        bull = (trend != 1) and (prev_close <= struct_high) and (close > struct_high)
        bear = (trend != -1) and (prev_close >= struct_low) and (close < struct_low)

        if bull or bear:
            if bull:
                trend = 1
                sl = struct_low - atr * SL_BUFFER_MULT
                sign = 1
                name = "BUY"
            else:
                trend = -1
                sl = struct_high + atr * SL_BUFFER_MULT
                sign = -1
                name = "SELL"
            entry = close
            risk = abs(entry - sl)
            cur = {"signal": name, "entry": entry, "sl": sl,
                   "tp1": entry + sign * risk * RR[0],
                   "tp2": entry + sign * risk * RR[1],
                   "tp3": entry + sign * risk * RR[2]}
            events.append(dict(cur, kind="signal", time_unix=t))
            long_watch = bull
            short_watch = bear
            away_buy = away_sell = True
            continue  # no zone-touch on the signal candle itself

        if cur is None:
            continue

        if long_watch and (b["low"] <= cur["sl"] or b["high"] >= cur["tp3"]):
            long_watch = False
        if short_watch and (b["high"] >= cur["sl"] or b["low"] <= cur["tp3"]):
            short_watch = False

        if long_watch and away_buy and b["low"] <= cur["entry"]:
            away_buy = False
            events.append(dict(cur, kind="touch", time_unix=t))
        if short_watch and away_sell and b["high"] >= cur["entry"]:
            away_sell = False
            events.append(dict(cur, kind="touch", time_unix=t))

        if long_watch and not away_buy and close > cur["entry"] + atr * ZONE_REARM_MULT:
            away_buy = True
        if short_watch and not away_sell and close < cur["entry"] - atr * ZONE_REARM_MULT:
            away_sell = True

    events.sort(key=lambda e: e["time_unix"])
    return events


def deliver_alert(ev, bars15):
    """Telegram (chart photo, text fallback) + push + history. Returns True if saved."""
    f = lambda v: "{:.2f}".format(v)
    symbol, signal, kind = "XAUUSD", ev["signal"], ev["kind"]
    entry, sl, tp1, tp2, tp3 = f(ev["entry"]), f(ev["sl"]), f(ev["tp1"]), f(ev["tp2"]), f(ev["tp3"])
    caption = build_caption(symbol, signal, kind, entry, sl, tp1, tp2, tp3)

    chart_sent = False
    chart_url_for_app = ""
    try:
        closes = [b["close"] for b in bars15[-120:]]
        if len(closes) > 10:
            config = build_chart_config(closes, ev["entry"], ev["sl"], ev["tp1"], ev["tp2"], ev["tp3"], signal)
            png = render_chart_png_bytes(config)
            r = send_photo_bytes(png, caption)
            chart_sent = r.status_code == 200
            if not chart_sent:
                print("Scan: Telegram photo failed:", r.status_code, r.text[:200])
            chart_url_for_app = ("/chart-image?signal=" + signal + "&entry=" + entry + "&sl=" + sl +
                                 "&tp1=" + tp1 + "&tp2=" + tp2 + "&tp3=" + tp3)
    except Exception as e:
        print("Scan: chart failed:", repr(e))
    if not chart_sent:
        try:
            send_text(caption)
        except Exception as e:
            print("Scan: Telegram text failed:", repr(e))

    new_entry = {
        "symbol": symbol, "signal": signal, "kind": kind,
        "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3,
        "chart_url": chart_url_for_app,
        "time": datetime.utcfromtimestamp(ev["time_unix"]).strftime("%d %b %Y, %H:%M UTC"),
        "time_unix": ev["time_unix"]
    }
    saved = False
    try:
        history, sha = gh_load_history()
        history.insert(0, new_entry)
        history.sort(key=lambda x: x.get("time_unix", 0), reverse=True)
        saved = gh_save_history(history[:MAX_HISTORY], sha)
    except Exception as e:
        print("Scan: history save failed:", repr(e))

    try:
        dot = "🟢" if signal == "BUY" else "🔴"
        title = dot + " " + signal + (" Setup" if kind == "signal" else " Zone Touched Again")
        send_push_to_all(title, "Entry " + entry + " | SL " + sl + " | TP1 " + tp1, "/")
    except Exception as e:
        print("Scan: push failed:", repr(e))
    return saved


@app.route("/scan-signals", methods=["GET"])
def scan_signals():
    force = request.args.get("force") == "1"
    dry = request.args.get("dry") == "1"
    if market_is_closed() and not force:
        return Response(json.dumps({"status": "market closed - skipped, no credits used"}), mimetype="application/json")
    if not BOT_TOKEN or not CHAT_ID:
        return Response(json.dumps({"error": "Telegram variables missing"}), status=500, mimetype="application/json")

    bars15 = fetch_ohlc(interval="15min", outputsize=300)
    bars1 = fetch_ohlc(interval="1min", outputsize=1500)
    if not bars15 or not bars1:
        return Response(json.dumps({"error": "Could not fetch candles (Twelve Data limit or key issue)"}),
                        status=502, mimetype="application/json")
    _ind_store(bars15, bars1)
    bars15 = drop_unfinished_bar(bars15, 900)
    bars1 = drop_unfinished_bar(bars1, 60)

    events = detect_events_dual_tf(bars15, bars1)
    now_ts = _time_mod.time()
    fresh = []
    for ev in events:
        age = now_ts - ev["time_unix"]
        limit = SCAN_RECENT_SIGNAL_SEC if ev["kind"] == "signal" else SCAN_RECENT_TOUCH_SEC
        if 0 <= age <= limit or force:
            fresh.append(ev)
    if not force:
        fresh = [e for e in fresh if (now_ts - e["time_unix"]) <= (SCAN_RECENT_SIGNAL_SEC if e["kind"] == "signal" else SCAN_RECENT_TOUCH_SEC)]
    else:
        fresh = fresh[-1:]  # force: only the single latest event, for testing

    try:
        history, _ = gh_load_history()
    except Exception:
        history = []
    seen = set((h.get("signal"), h.get("kind"), h.get("time_unix")) for h in history)

    def near_duplicate(ev):
        # an older TradingView-webhook entry for the same setup (time differs by seconds/minutes)
        for h in history:
            if h.get("signal") == ev["signal"] and h.get("kind") == ev["kind"]:
                try:
                    if abs(int(h.get("time_unix", 0)) - ev["time_unix"]) <= 300:
                        return True
                except Exception:
                    pass
        return False

    new_events = [e for e in fresh if (e["signal"], e["kind"], e["time_unix"]) not in seen and not near_duplicate(e)]
    if force:
        new_events = fresh  # test mode resends even if already seen

    sent = 0
    if not dry:
        for ev in new_events:
            deliver_alert(ev, bars15)
            sent += 1

    return Response(json.dumps({
        "status": "ok", "bars": {"15m": len(bars15), "1m": len(bars1)},
        "last_candle_utc": datetime.utcfromtimestamp(bars1[-1]["time"]).strftime("%d %b %H:%M"),
        "events_in_window": len(events), "fresh": len(fresh), "new_alerts_sent": sent,
        "dry_run": dry
    }), mimetype="application/json")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
