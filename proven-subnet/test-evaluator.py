# test_evaluator.py
import os
import sys
sys.path.insert(0, '.')

# Paste just the evaluate_miner function here standalone, no Bittensor needed
import tempfile
import subprocess

def evaluate_miner(script_content: str) -> float:
    if not script_content:
        return 0.0

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        script_path = f.name

    try:
        subprocess.run(["python", "-m", "py_compile", script_path], check=True, capture_output=True)

        env = {**os.environ, "TARGET_URL": "http://localhost:8080"}
        res_clean = subprocess.run(
            ["pytest", script_path, "--tb=short", "--browser", "chromium"],
            env=env, capture_output=True, text=True, timeout=60
        )
        if res_clean.returncode != 0:
            print("❌ Failed Reference Gate")
            print(res_clean.stdout)
            return 0.0

        env_mutant = {**os.environ, "TARGET_URL": "http://localhost:8081"}
        res_mutant = subprocess.run(
            ["pytest", script_path, "--tb=short", "--browser", "chromium"],
            env=env_mutant, capture_output=True, text=True, timeout=60
        )
        if res_mutant.returncode != 0:
            print("✅ Mutant killed! Score: 1.0")
            print(res_mutant.stdout)
            return 1.0
        else:
            print("❌ Mutant survived. Score: 0.0")
            return 0.0

    except subprocess.CalledProcessError:
        print("❌ Syntax error in script")
        return 0.0
    finally:
        os.remove(script_path)


# Hardcoded test script — same as what your miner generates
TEST_SCRIPT = """
import os
from playwright.sync_api import Page, expect

TARGET_URL = os.environ.get("TARGET_URL", "http://localhost:8080")

def test_willify_core_features(page: Page):
    page.goto(f"{TARGET_URL}/src/html/index.html")
    
    read_more_btn = page.locator("#read-more-button")
    expect(read_more_btn).to_be_visible()
    
    heading = page.locator("h3")
    expect(heading).to_have_text("Where Music Meets Comfort")
    
    register_btn = page.locator("#sign-up")
    expect(register_btn).to_have_attribute("href", "register.html")
"""

score = evaluate_miner(TEST_SCRIPT)
print(f"\nFinal score: {score}")