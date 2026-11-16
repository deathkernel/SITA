# SITA n8n Automation Library

This directory stores **importable n8n workflow JSON files** for local automation experiments alongside SITA-App.

## Boundary and safety

- n8n is a separate local workflow engine; these files do not add n8n as a runtime dependency of SITA-App.
- Existing SITA application code and behavior are unchanged by this starter pack.
- Workflows are imported into the user's own n8n instance and remain inactive until explicitly activated.
- Credentials, API keys, passwords, and personal data must be configured inside n8n Credentials or local environment variables. Never commit secrets in workflow JSON.
- Review every workflow and its external connections before activation. A workflow can call external services and may transmit data.
- This starter workflow uses only built-in nodes and does not require credentials or external API calls.

## Included workflows

| File | Purpose | Credentials |
|---|---|---|
| [01-hello-world-conditional.json](workflows/01-hello-world-conditional.json) | Manual trigger, create a message, transform it with JavaScript, branch on status, and emit a success/failure result | None |

## Import into local n8n

1. Open your local n8n instance, normally `http://localhost:5678`.
2. Create a new workflow (or open the workflow menu).
3. Choose **Import from File**.
4. Select the desired `.json` file from this directory.
5. Inspect the imported nodes and connections.
6. Click **Execute Workflow** to test it.
7. Save it. Keep it inactive until you intentionally want an automated trigger to run.

## Test the success and failure branches

The starter workflow defaults to `status: "Success"`, so the IF node routes to **Success Result**.

To test the other path, open **Process Message**, temporarily change `status: "Success"` to `status: "Failed"`, execute again, and confirm **Failure Result**. Restore `"Success"` afterward.

## Compatibility

The workflow uses standard n8n core nodes: Manual Trigger, Edit Fields (Set), Code, and IF. If your installed n8n version reports a node-version migration prompt, review the converted workflow before saving.

## Next additions

New workflows should be numbered, self-contained JSON exports and documented here with purpose, required credentials, data-flow notes, and activation instructions. Do not add credentials or machine-specific absolute paths to committed workflow files.
