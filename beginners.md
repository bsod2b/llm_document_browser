# Beginners Guide

In case anything is unclear or you need help feel free to DM me about it! No shame, even if you feel dumb af: I can tell you - I've been there too. And instead of bashing your head against a wall for 12 hours, you'll be better off just asking for help. Yes, I am speaking from experience. I accept payments in form of piwo's (this is a joke, I do this for fun)

## Setup
No more yapping, let's dive straight in. You'll need a certain setup in order to actual develop. Feel free to browse on your own but the easiest options (and where I can help you out the most) will be the following:

- [VS Code](https://code.visualstudio.com/download): This is your development environment where you'll edit your files, as well as launch them.
- [Python](https://www.python.org/downloads): This will be the programming language we'll be using. I am using the version 3.12.11. For you, switching to [3.12.10](https://www.python.org/downloads/release/python-31210/) will be okay too, as it is easier to install. It would be rare if you're using Windows and are not on amd64.
- [Git](https://git-scm.com/downloads): You'll need git to clone this repository. If you can't figure out the next step, you could also try GitHub Desktop. If you can't bother, I guess copy-pasting the files would work too (even if it hurts my soul).

## Cloning the Repository from GitHub

To get started, you'll want to clone this project to your local machine. Follow these steps:

1. Click the green **Code** button and copy the URL (it should look like `https://github.com/bsod2b/llm_document_browser.git`).
2. Open a terminal and navigate to the folder where you want to store the project (don't be scared of the scary terminal).
3. Run the following command, replacing the URL with the one you copied:

    ```bash
        git clone https://github.com/bsod2b/llm_document_browser.git
    ```

4. Change into the project directory:

    ```bash
        cd llm_document_browser
    ```

Now you have a local copy of the project and can start working!

## Virtual environment & API-Keys
That'll be all already, since we will be developing in a virtual environment. 
Open VSCode and open a this folder running the following command in your project directory:

```bash
python -m venv .venv
```

This will create a new virtual environment named `.venv` in your current folder. Now we install the other requirements in this virtual environment:

```bash
pip install -r requirements.txt
```

We are not making our own LLM from scratch as I don't have a few thousand dollars and thousands of GPUs lying around. Therefore, we will just be building a ChatGPT Wrapper. As I don't want to host my own instance too, we'll be using their API. Create a new file in the root project directory called `.env.` and add the following line.

```
OPENAI_API_KEY="<your-api-key>"
```

Replace the `<your-api-key>` with the one you generated [here](https://platform.openai.com/api-keys)

