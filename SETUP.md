# Setup

Setting up takes about twenty minutes the first time, most of it waiting
for downloads, and needs about 1.5 GB of free disk space (about 3 GB on a Mac
that doesn't yet have Apple's command-line tools, which bring git). Besides
your WRDS class account, you need no accounts: not even one on GitHub.

## The terminal

You set everything up by typing commands into a terminal, a window where
you type instructions instead of clicking. Every computer has one:

- On a Mac, Terminal: press Command and Space together, type Terminal, and
  press Return.
- On Windows, PowerShell: open the Start menu, type PowerShell, and click
  Windows PowerShell. (Not "Run as administrator".)

Each box below holds one command. For each one, in order:

1. Copy it. On GitHub, the button at the right of the box copies it.
2. Paste it into the terminal (Command-V on a Mac, Ctrl-V on Windows) and
   press Return (Enter on Windows).
3. Wait until the terminal is ready for the next command: it shows a new
   line ending in `%` on a Mac, or `>` on Windows.

Then go on to the next box. Never paste two commands at once.

## 1. Install uv and git

`uv` installs Python and every package the code uses, in a folder of its
own, so it won't disturb anything else on your computer. `git` downloads the
code and, later, its updates.

On a Mac, install uv:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then install git, which comes with Apple's command-line tools:

```
xcode-select --install
```

A window opens: click Install, agree, and wait for it to finish, which can
take ten minutes or more. If the terminal says the tools are already
installed, you already have git. (If you use Homebrew, `brew install uv git`
does both.)

On Windows, install uv:

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then install git:

```
winget install --id Git.Git -e --source winget
```

If it asks whether you agree to the terms, type Y and press Enter; if a
window asks whether to allow changes, click Yes.

Then close the terminal and open a new one, so that it finds the new
commands.

## 2. Get the code

The code goes in your home folder, the folder named after you, where the
terminal starts. (Not on the Desktop or in Documents: iCloud and OneDrive
often copy those online, and the data must stay on your own computer.)
Download the code:

```
git clone https://github.com/rorymullen/fnce_3030_portfolio_strategies.git
```

That makes a folder, `fnce_3030_portfolio_strategies`, in your home folder.
Move into it:

```
cd fnce_3030_portfolio_strategies
```

Every command from here on runs inside that folder. Whenever you open a new
terminal, run that `cd` command first.

To see the folder, open it in a window. On a Mac:

```
open .
```

On Windows:

```
explorer .
```

To find it again later: on a Mac, in Finder choose Go, then Home; on
Windows, in File Explorer open This PC, then Local Disk (C:), then Users,
then your name.

On a Windows laptop with an ARM processor, such as a Snapdragon, run this
once in that folder before anything else, because some of the packages the
code uses aren't built for ARM yet. (To check: Settings, then System, then
About; "System type" says ARM-based.)

```
uv python pin cpython-3.13-windows-x86_64-none
```

(Without git, the green Code button on the repository's GitHub page offers
Download ZIP. Unzip it and open a terminal in that folder. You then get
updates by downloading again and copying your `my_strategy.py` across.)

Your work stays on your own computer. Don't fork the repository on GitHub:
a fork of a public repository is public too, and so would be your strategy.

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

```
uv run step1_download.py
```

The first time you run anything, uv also installs Python and the packages,
which adds a minute or two. Type your WRDS username and press Return, then
your password and Return. Nothing shows as you type the password; that is
normal. When step 1 asks, open Duo Mobile on your phone and tap Approve.

Then build the monthly table:

```
uv run step2_prepare.py
```

And run the serious example:

```
uv run run.py examples/gross_profitability.py
```

That writes the example's factsheet. Open it. On a Mac:

```
open results/gross_profitability/factsheet.pdf
```

On Windows:

```
start results\gross_profitability\factsheet.pdf
```

If you can read it, everything works. Now write your own signal in
`my_strategy.py` and run

```
uv run run.py my_strategy.py
```

Then open its factsheet. On a Mac:

```
open results/my_strategy/factsheet.pdf
```

On Windows:

```
start results\my_strategy\factsheet.pdf
```

You only run steps 1 and 2 again if you delete the files in `data/`.

## 5. Updates

When the course adds or fixes something, bring it in, inside the folder,
with

```
git pull
```

The course never changes `my_strategy.py`, so an update never touches your
work. If you changed other files and git stops with a message about them,
paste the message into an AI tool and ask what to do.

## When something goes wrong

Read the message. The code stops with a sentence saying what went wrong
and, usually, what to do next. If the terminal says a command is not found,
close it, open a new one, `cd` into the folder, and try again. If that
doesn't settle it, tell an AI tool what you ran, paste the whole message you
saw, and ask what went wrong. Never paste your password or rows of the data.
