cd /tmp/claude-0/-home-user-FamilyDB/3d9e6f71-716a-5f05-abd6-33b8701ac8dd/scratchpad/judge16
claude -p "Your folder is the current directory. Read BRIEF.md here and do everything it asks, working only in this folder." --model claude-opus-5-5 --permission-mode acceptEdits --allowedTools "Bash Read Write Edit Glob Grep" > reply.md 2> err.log
echo "judge exit $?" > ../judge16-done.log
