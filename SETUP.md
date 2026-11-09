# Setup

Setting up takes about twenty minutes the first time, most of it waiting
for downloads, and needs about 1.5 GB of free disk space (about 3 GB on a Mac
that doesn't yet have Apple's command-line tools, which bring git). You type a few commands into a terminal: Terminal on a Mac (in
Applications, then Utilities), or PowerShell on Windows (open the Start menu
and type "PowerShell"). Copy each command exactly, press Enter, and wait for
it to finish before the next.

## 1. Install uv and git

`uv` installs Python and every package the code uses, in a folder of its
own, so it won't disturb anything else on your computer. `git` downloads the
code and, later, its updates.

On a Mac:

    curl -LsSf https://astral.sh/uv/install.sh | sh
    xcode-select --install

The second command installs git with Apple's command-line tools: click
Install in the window that opens, and wait for it to finish. If it says they
are already installed, you already have git. (If you use Homebrew,
`brew install uv git` does both.)

On Windows:

    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    winget install --id Git.Git -e --source winget

Then close the terminal and open a new one, so that it finds the new
commands, and check that both work:

    uv --version
    git --version

Each should print a version number.

## 2. Get the code

Choose a folder that iCloud Drive or OneDrive doesn't sync, because the data
you download must stay on your own computer. Your home folder is fine, and
the terminal starts there. Copy the course repository into it:

    cd ~
    git clone https://github.com/rorymullen/fnce_3030_portfolio_strategies.git
    cd fnce_3030_portfolio_strategies

Every command from here on runs inside that folder. If you close the
terminal, open a new one and `cd` back into it first.

On a Windows laptop with an ARM processor, such as a Snapdragon, run this
once in that folder before anything else, because some of the packages the
code uses aren't built for ARM yet. (To check: Settings, then System, then
About; "System type" says ARM-based.)

    uv python pin cpython-3.13-windows-x86_64-none

(Without git, the green Code button on the repository's GitHub page offers
Download ZIP. Unzip it and open a terminal in that folder. You then get
updates by downloading again and copying your `my_strategy.py` across.)

### Keep your work private

Don't fork the repository on GitHub: a fork of a public repository is public
too, and so would be your strategy. Your work is safe on your own computer.
If you want a copy on GitHub as well, create a new **private** repository
there, empty (no README), and point your folder at it:

    git remote rename origin course
    git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
    git push -u origin main

From then on, save your work to your private repository with

    git add -A
    git commit -m "What I changed"
    git push

and bring in the course's updates with `git pull course main`. The first
commit may ask you to tell git your name and email, and says how. The first push asks
you to sign in to GitHub; GitHub's own tool makes that easy
(`gh auth login`, from [cli.github.com](https://cli.github.com)).

## 3. Register with WRDS

The data come from WRDS (Wharton Research Data Services), through CU's
subscription. The sign-up link and the class code are on Canvas, never in
this repository.

When you register, WRDS sets up Duo two-factor login. Choose Duo Mobile, the
phone app, so that you can approve a login with one tap: step 1 waits for
you to approve it.

## 4. The first run

Step 1 downloads the data, about 100 MB, and takes a few minutes. Run it
yourself, never through an AI tool: it asks for your WRDS username and
password, and your password should never pass through anything but your own
keyboard.

    uv run step1_download.py

The first time you run anything, uv also installs Python and the packages,
which adds a minute or two. When step 1 asks, open Duo Mobile on your phone
and tap Approve. Then build the monthly table, and run the serious example:

    uv run step2_prepare.py
    uv run run.py examples/gross_profitability.py

The last command writes `results/gross_profitability/factsheet.pdf`. Open
it: if you can read it, everything works. Now write your own signal in
`my_strategy.py` and run

    uv run run.py my_strategy.py

You only run steps 1 and 2 again if you delete the files in `data/`.

## 5. Updates

When the course adds or fixes something, bring it in with

    git pull

(or `git pull course main` if you made a private copy as above). The
course never changes `my_strategy.py`, so an update never touches your work.
If you changed other files and git stops with a message about them, paste
the message into an AI tool and ask what to do.

## When something goes wrong

Read the message. The code stops with a sentence saying what went wrong
and, usually, what to do next. If that doesn't settle it, tell an AI tool
what you ran, paste the whole message you saw, and ask what went wrong.
Never paste your password or rows of the data.
