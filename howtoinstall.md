# HOWTOINSTALL

This guide shows how to set up and run the **muon wire estimator** in two environments:

* **Local Ubuntu + VS Code**
* **CERN lxplus**

It starts from installing Python and ends with running a simple example.

---

## 1. What you need

The project needs:

* **Python 3.10 or newer**
* **git**
* internet access during setup so `pip` can install packages

Optional:

* **VS Code** for editing and running from an integrated terminal
* plotting support via `matplotlib`

---

## 2. Repository layout assumptions

This guide assumes your repository contains:

* `pyproject.toml`
* `muon_wire_estimator/`
* `scripts/setup_venv_local.sh`
* `scripts/setup_venv_lxplus.sh`
* `scripts/run_estimator.py`
* `scripts/run_event_scan.py`
* `examples/level1_example.json`
* `examples/level2_event_scan.json`

---

## 3. Local Ubuntu setup

### Step 1: Install Python locally

Open a terminal and run:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

Check the version:

```bash
python3 --version
```

You want Python **3.10+**.

---

### Step 2: Clone the repository

```bash
git clone <your-repo-url>
cd muon_wire_estimator
```

If you already downloaded the repo another way, just `cd` into it.

---

### Step 3: Create and install the virtual environment

Run:

```bash
./scripts/setup_venv_local.sh
```

This script will:

* create `.venv`
* activate it internally
* upgrade `pip`, `setuptools`, and `wheel`
* install the package
* install plotting dependencies if enabled

If the script is not executable yet, first run:

```bash
chmod +x scripts/setup_venv_local.sh
```

---

### Step 4: Activate the environment

```bash
source .venv/bin/activate
```

Your shell prompt should now show something like:

```bash
(.venv)
```

---

### Step 5: Verify the install

Run these checks:

```bash
python -c "import muon_wire_estimator; print('import ok')"
python scripts/run_estimator.py --help
python scripts/run_event_scan.py --help
```

If all three work, the installation is good.

---

### Step 6: Run a simple deterministic example

```bash
python scripts/run_estimator.py \
  --config examples/level1_example.json \
  --pretty
```

To write the result to a file:

```bash
python scripts/run_estimator.py \
  --config examples/level1_example.json \
  --output out/level1_result.json \
  --pretty
```

---

### Step 7: Run a simple stochastic example

```bash
python scripts/run_event_scan.py \
  --config examples/level2_event_scan.json \
  --pretty
```

To write the result to a file:

```bash
python scripts/run_event_scan.py \
  --config examples/level2_event_scan.json \
  --output out/level2_result.json \
  --pretty
```

---

## 4. Using VS Code on Ubuntu

### Open the project

From the repo root:

```bash
code .
```

If `code` is not found, open VS Code manually and choose **File → Open Folder**.

---

### Select the correct Python interpreter

In VS Code:

1. Press `Ctrl+Shift+P`
2. Search for `Python: Select Interpreter`
3. Choose:

```bash
.venv/bin/python
```

This makes VS Code use the local project environment.

---

### Use the integrated terminal

Open a VS Code terminal and activate the venv if needed:

```bash
source .venv/bin/activate
```

Then run the same example commands as above.

---

## 5. lxplus setup

### Step 1: Log in and go to the repo

```bash
cd /afs/cern.ch/user/<first-letter>/<username>/.../muon_wire_estimator
```

Or clone the repo first if needed:

```bash
git clone <your-repo-url>
cd muon_wire_estimator
```

---

### Step 2: Make the lxplus setup script executable

```bash
chmod +x scripts/setup_venv_lxplus.sh
```

---

### Step 3: Run the lxplus setup script

```bash
./scripts/setup_venv_lxplus.sh
```

This script is meant to be safer on lxplus because it clears common inherited environment variables that can interfere with a local venv.

If needed, you can explicitly choose a Python version:

```bash
PYTHON_BIN=python3 ./scripts/setup_venv_lxplus.sh
```

If lxplus has multiple Python executables and you know the exact one you want, use that instead.

---

### Step 4: Activate the environment

```bash
source .venv/bin/activate
```

Check that Python and pip are coming from the venv:

```bash
which python
which pip
python --version
```

You want both `python` and `pip` to point inside `.venv/`.

---

### Step 5: Verify the install

```bash
python -c "import muon_wire_estimator; print('import ok')"
python scripts/run_estimator.py --help
python scripts/run_event_scan.py --help
```

---

### Step 6: Run the example jobs

Deterministic example:

```bash
python scripts/run_estimator.py \
  --config examples/level1_example.json \
  --output out/level1_result.json \
  --pretty
```

Stochastic example:

```bash
python scripts/run_event_scan.py \
  --config examples/level2_event_scan.json \
  --output out/level2_result.json \
  --pretty
```

Inspect the outputs:

```bash
sed -n '1,80p' out/level1_result.json
sed -n '1,80p' out/level2_result.json
```

---

## 6. Plotting support

If your `pyproject.toml` includes a plotting extra like:

```toml
[project.optional-dependencies]
plot = ["matplotlib>=3.7"]
```

then the setup scripts can install plotting automatically.

If needed, you can also install it manually after activating the venv:

```bash
python -m pip install -e ".[plot]"
```

Then run your plotting script, for example:

```bash
python scripts/plot_sweeps.py
```

---

## 7. Common problems

### Problem: `python` is too old

Check:

```bash
python3 --version
```

You need Python **3.10+**.

---

### Problem: `ModuleNotFoundError: No module named 'muon_wire_estimator'`

Usually this means one of these:

* the package was not installed yet
* the venv is not activated
* the repo structure is wrong

Try:

```bash
source .venv/bin/activate
python -m pip install -e .
python -c "import muon_wire_estimator; print('import ok')"
```

---

### Problem: plotting fails because `matplotlib` is missing

Install the plotting extra:

```bash
python -m pip install -e ".[plot]"
```

---

### Problem: lxplus pulls in strange external packages

Use the lxplus setup script instead of the local one:

```bash
./scripts/setup_venv_lxplus.sh
```

and verify:

```bash
which python
which pip
```

Both should point into `.venv/`.

---

## 8. Minimal quick-start summary

### Local Ubuntu

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git

git clone <your-repo-url>
cd muon_wire_estimator
chmod +x scripts/setup_venv_local.sh
./scripts/setup_venv_local.sh
source .venv/bin/activate
python scripts/run_estimator.py --config examples/level1_example.json --pretty
```

### lxplus

```bash
cd /path/to/muon_wire_estimator
chmod +x scripts/setup_venv_lxplus.sh
./scripts/setup_venv_lxplus.sh
source .venv/bin/activate
python scripts/run_estimator.py --config examples/level1_example.json --output out/level1_result.json --pretty
```

---

## 9. Recommended next checks

After installation, a good first test sequence is:

```bash
python -c "import muon_wire_estimator; print('import ok')"
python scripts/run_estimator.py --help
python scripts/run_event_scan.py --help
python scripts/run_estimator.py --config examples/level1_example.json --pretty
python scripts/run_event_scan.py --config examples/level2_event_scan.json --pretty
```

If all of these succeed, the environment is ready.
