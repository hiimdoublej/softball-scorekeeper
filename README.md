# Softball Scorekeeper

A Codex skill for turning a softball recording into a chronological scorebook. The scoring instructions and review interface are in Traditional Chinese. The workflow covers batting outcomes, runner and out counts, missing footage, team corrections, and estimated offensive WPA for completed games.

## Install the skill

Clone this repository into your personal Codex skills directory, naming the checkout `softball-scorekeeper`. Replace `OWNER/REPO` with this repository's GitHub owner and name.

Windows PowerShell:

```powershell
git clone https://github.com/OWNER/REPO.git "$env:USERPROFILE/.codex/skills/softball-scorekeeper"
```

macOS or Linux:

```sh
git clone https://github.com/OWNER/REPO.git ~/.codex/skills/softball-scorekeeper
```

If you use a custom Codex home, use its skills directory instead. Start a new Codex chat, supply a recording, and try:

> 用 $softball-scorekeeper 分析這場比賽。我隊先攻，穿白色球衣。請記錄每個打席、背號、得分與判讀依據，再列出進攻 WPA 前十名。

## Run the local clip finder

From this checkout, with Python 3.9 or newer and a local recording:

```sh
python -m pip install -r requirements.txt
python scripts/analyze.py "/path/to/game.mp4" Game1
```

Open the generated `game-review.html` beside the original video. It includes candidate clips and the intervals between them. Review those intervals for quiet plays, enter results, then export the ledger as CSV. The activity score ranks moments for review. Assign result confidence after checking the play itself. The browser saves manual entries locally.

The standalone clip finder produces a review page. For the full mobile scorecard, use the skill workflow and the [WPA and mobile scoring reference](references/wpa-mobile.md). The bundled WPA model uses the observed offensive turns and assumes equal-strength teams. Its percentages are estimates for completed games.
