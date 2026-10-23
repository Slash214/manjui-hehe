"""Create a local sample through the real API; no media is fabricated."""
import json
import os
from pathlib import Path

import httpx

client = httpx.Client(base_url=os.getenv("API_URL", "http://127.0.0.1:8000") + "/api/v1", timeout=30)
credentials = {"email": "demo@manju.local", "password": "Manju-Local-2026!"}
response = client.post("/auth/register", json=credentials)
if response.status_code == 409:
    response = client.post("/auth/login", json=credentials)
response.raise_for_status()
client.headers["Authorization"] = "Bearer " + response.json()["access_token"]


def post(path: str, **data):
    response = client.post(path, json=data)
    response.raise_for_status()
    return response.json()


project = post("/projects", name="大唐小饭馆", style_prompt="唐代市井，写实光影，温暖木色")
episode = post(f"/projects/{project['id']}/episodes", title="一碗饭的转机", episode_no=1)
asset_versions = []
assets = {}
for name, kind in [("沈知味", "character"), ("掌柜", "character"), ("饭馆大堂", "location"), ("后厨", "location"), ("饭碗", "prop")]:
    asset = post(f"/projects/{project['id']}/assets", name=name, asset_type=kind)
    assets[name] = asset['id']
    version = post(f"/assets/{asset['id']}/versions", base_version=1, description=name)
    asset_versions.append(version['id'])
scenes = []
for index, (title, texts) in enumerate([
    ("饭馆大堂", ["三个月房租，今天必须结清！", "掌柜的，您先坐，容我做碗饭，吃完再说。"]),
    ("后厨", ["沈知味颠勺，火光腾起。", "一碗蛋炒饭，粒粒分明。"]),
    ("饭馆大堂", ["……再来一碗。"]),
]):
    scene = post(f"/episodes/{episode['id']}/scenes", title=title, order_no=index, location_asset_id=assets[title])
    lines = [post(f"/scenes/{scene['id']}/lines", text=text, order_no=i,
                  line_type="action" if index == 1 and i == 0 else "narration" if index == 1 else "dialogue",
                  character_asset_id=assets['掌柜'] if index != 1 and i == 0 else assets['沈知味'] if index == 0 else None)
             for i, text in enumerate(texts)]
    scenes.append((scene, lines))
post(f"/episodes/{episode['id']}/script/confirm", base_version=1, note="附录示例")
shots = []
for index, action in enumerate(["饭馆大堂，掌柜坐在桌前", "掌柜拍桌，催讨房租", "沈知味抬头，平静回应", "沈知味转身走向后厨", "灶火升起，饭粒落入锅中", "沈知味颠勺，火光腾起", "蛋炒饭盛入碗中", "沈知味端饭回到大堂", "掌柜尝一口饭", "掌柜放下碗，沉默片刻", "掌柜低声说：再来一碗"]):
    group = 0 if index < 4 else 1 if index < 7 else 2
    scene, lines = scenes[group]
    shot = post(f"/episodes/{episode['id']}/shots", scene_id=scene['id'], order_no=index, action_desc=action,
                est_duration_ms=6000 if index in [1,2,10] else 4500, blocking_desc="人物视线保持一致")
    response = client.put(f"/shots/{shot['id']}/refs", json={"base_version": 1, "asset_version_ids": asset_versions[:3]})
    response.raise_for_status()
    if index in [1,2,5,10]:
        response = client.put(f"/shots/{shot['id']}/lines", json={"base_version": 2, "line_ids": [lines[-1]['id']]})
        response.raise_for_status()
    shots.append(shot)
url = os.getenv("FRONTEND_URL", "http://127.0.0.1:5173") + f"/episodes/{episode['id']}/director?shot={shots[1]['id']}"
result = {"url": url, "email": credentials['email'], "project_id": project['id'], "episode_id": episode['id']}
(Path(__file__).resolve().parents[1] / os.getenv('DEMO_FILE', 'docs/demo.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(url)
