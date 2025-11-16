The store_path and activity file are failign to write. Help me debug this. First review the logs below. Then use subagents to search the code and identify the root
  cause. Make the code changes then run `make up` once the command is complete sleep for 180 seconds. Then exec into the container and confirm the fix worked. If it
  didn't rollback you changes to the current commit and start again. Always delegate this loop to a subagnet. Detailed logs can be found at app/lot.txt in the
  container. 