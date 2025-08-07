# Contributing to Atlas

We follow a set of guidelines to ensure the `main` branch is always stable and that changes are introduced in a structured way. All development, no matter how small, should be done in a feature branch and merged via a Pull Request.

## The Golden Rule: Never Push Directly to `main`

The `main` branch is protected by a GitHub Actions workflow that will automatically reject any direct push. This is intentional.

## The Correct Workflow

1.  **Create a New Branch:** Before you start any work, pull the latest changes from `main` and create a new, descriptively named branch.

    ```bash
    # Make sure your main branch is up-to-date
    git checkout main
    git pull origin main

    # Create your new branch
    # Good branch names: feature/instapaper-api, fix/parsing-error, docs/update-readme
    git checkout -b <branch-name>
    ```

2.  **Do Your Work:** Make all your code changes, additions, and deletions on your feature branch.

3.  **Run the Health Check:** Before committing, always run the health check script to catch any issues early.

    ```bash
    bash run_atlas.sh
    # (Let the health check run, then you can exit without running the full pipeline)
    ```

4.  **Commit Your Changes:** Make one or more logical commits to your branch. Write clear and concise commit messages.

    ```bash
    git add .
    git commit -m "feat(parser): Add support for a new data source"
    ```

5.  **Push Your Branch:** Push your feature branch to the remote repository.

    ```bash
    git push origin <branch-name>
    ```

6.  **Create a Pull Request:** Go to the project's GitHub page. You will see a prompt to create a new Pull Request from your recently pushed branch.

    *   Give the Pull Request a clear title.
    *   In the description, briefly explain the changes you made.
    *   Submit the Pull Request.

7.  **Merge the Pull Request:** Once any automated checks pass (and after a review, if necessary), you can merge the Pull Request into the `main` branch.
