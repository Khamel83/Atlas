#!/bin/bash

# This script is the recommended way to run the Atlas pipeline.
# It first performs a health check and then runs the main application.

# --- Colors for output ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# --- Script ---

# 1. Run the health check script
echo -e "${GREEN}--- Running Atlas Health Check ---${NC}"
python3 scripts/health_check.py
HEALTH_CHECK_STATUS=$?

if [ $HEALTH_CHECK_STATUS -ne 0 ]; then
    echo -e "${YELLOW}Health check script failed to run. Please check 'scripts/health_check.py'.${NC}"
    exit 1
fi

echo -e "\n--- Health Check Complete ---"

# 2. Comprehensive TODO Consolidation and Development Workflow
echo -e "\n${BLUE}--- Atlas TODO Consolidation & Development ---${NC}"
echo "Atlas maintains a comprehensive TODO tracking system across all sources:"
echo "  • Cursor TODO system"
echo "  • Development task JSON files"
echo "  • Inline code TODO/FIXME comments"
echo "  • Documentation task references"
echo "  • Roadmap and checklist files"
echo ""
echo "First, let's consolidate all TODOs to get the complete picture..."
echo ""

# Initialize unified TODO system
echo -e "${YELLOW}Initializing unified TODO management system...${NC}"
python3 scripts/unified_todo_manager.py --import
TODO_STATUS=$?

if [ $TODO_STATUS -ne 0 ]; then
    echo -e "${RED}TODO system initialization failed. Continuing with existing workflow...${NC}"
fi

echo ""
echo "Development workflow options:"
echo "  1. Skip development - Go straight to main pipeline"
echo "  2. View unified task dashboard - See consolidated TODO status"
echo "  3. Run automated development - Work on priority tasks automatically"
echo "  4. Interactive development - Choose specific tasks to work on"
echo "  5. Interactive TODO management - Add, update, complete TODOs"
echo ""

read -p "Choose development option (1-5): " dev_choice

case $dev_choice in
    1)
        echo -e "${GREEN}Skipping development workflow...${NC}"
        ;;
    2)
        echo -e "${BLUE}Displaying unified task dashboard...${NC}"
        python3 scripts/unified_todo_manager.py --dashboard
        echo ""
        read -p "Press Enter to continue to main pipeline..."
        ;;
    3)
        echo -e "${BLUE}Running automated development...${NC}"
        echo "This will work on the highest priority tasks from the consolidated TODO system."
        python3 scripts/dev_workflow.py --auto
        DEV_STATUS=$?
        if [ $DEV_STATUS -ne 0 ]; then
            echo -e "${RED}Development workflow encountered issues. Check logs.${NC}"
            read -p "Continue to main pipeline anyway? (y/N): " continue_anyway
            if [[ ! $continue_anyway =~ ^[Yy]$ ]]; then
                echo "Exiting."
                exit 1
            fi
        fi
        # Sync TODO system after development work
        echo -e "${YELLOW}Syncing TODO system after development work...${NC}"
        python3 scripts/unified_todo_manager.py --sync
        ;;
    4)
        echo -e "${BLUE}Starting interactive development mode...${NC}"
        python3 scripts/dev_workflow.py
        echo ""
        # Sync TODO system after interactive work
        echo -e "${YELLOW}Syncing TODO system after development work...${NC}"
        python3 scripts/unified_todo_manager.py --sync
        echo ""
        read -p "Development complete. Continue to main pipeline? (y/N): " continue_pipeline
        if [[ ! $continue_pipeline =~ ^[Yy]$ ]]; then
            echo "Exiting."
            exit 0
        fi
        ;;
    5)
        echo -e "${BLUE}Managing TODOs with unified system...${NC}"
        python3 scripts/unified_todo_manager.py --interactive
        echo ""
        read -p "Continue to main pipeline? (y/N): " continue_pipeline
        if [[ ! $continue_pipeline =~ ^[Yy]$ ]]; then
            echo "Exiting."
            exit 0
        fi
        ;;
    *)
        echo -e "${YELLOW}Invalid choice. Continuing to main pipeline...${NC}"
        ;;
esac

# 3. Ask the user what they want to run
echo -e "\n${GREEN}--- Atlas Main Pipeline ---${NC}"
echo -e "What would you like to run? (Select one or more options)"
echo "1. All ingestion types"
echo "2. Articles only"
echo "3. Podcasts only"
echo "4. YouTube only"
echo "5. Instapaper only"
echo "6. Process URLs from a file"
echo "7. Run recategorization"
echo "q. Quit"

# Read user input
read -p "Enter your choice(s) (e.g., '1' or '2 7' for multiple): " choices

# Process user choices
run_args=""
for choice in $choices; do
    case $choice in
        1)
            run_args="$run_args --all"
            ;;
        2)
            run_args="$run_args --articles"
            ;;
        3)
            run_args="$run_args --podcasts"
            ;;
        4)
            run_args="$run_args --youtube"
            ;;
        5)
            run_args="$run_args --instapaper"
            ;;
        6)
            read -p "Enter the path to the URL file: " url_file
            run_args="$run_args --urls $url_file"
            ;;
        7)
            run_args="$run_args --recategorize"
            ;;
        q|Q)
            echo "Exiting."
            exit 0
            ;;
        *)
            echo -e "${YELLOW}Invalid choice: $choice${NC}"
            ;;
    esac
done

if [ -z "$run_args" ]; then
    echo -e "${YELLOW}No valid choices selected. Exiting.${NC}"
    exit 1
fi

# 4. Run the main application with the selected options
echo -e "\n${GREEN}--- Starting Atlas Main Pipeline ---${NC}"
echo -e "Running with arguments: $run_args"
python3 run.py $run_args
PIPELINE_STATUS=$?

echo -e "\n${GREEN}--- Pipeline Finished ---${NC}"

# 5. Post-pipeline development check
if [ $PIPELINE_STATUS -eq 0 ]; then
    echo -e "${GREEN}Pipeline completed successfully!${NC}"
    
    # Check if there are any new issues that need attention
    echo -e "\n${BLUE}--- Post-Pipeline Development Check ---${NC}"
    echo "Checking for any new issues or improvements needed..."
    
    # Sync TODO system to capture any new issues
    echo -e "${YELLOW}Syncing TODO system after pipeline run...${NC}"
    python3 scripts/unified_todo_manager.py --sync
    
    # Run a quick task assessment
    python3 scripts/dev_workflow.py --quick-assessment
    
    echo ""
    read -p "Run post-pipeline development workflow? (y/N): " post_dev
    if [[ $post_dev =~ ^[Yy]$ ]]; then
        python3 scripts/dev_workflow.py --auto
        # Final TODO system sync
        echo -e "${YELLOW}Final TODO system sync...${NC}"
        python3 scripts/unified_todo_manager.py --sync
    fi
else
    echo -e "${RED}Pipeline encountered errors. Exit code: $PIPELINE_STATUS${NC}"
    echo -e "${YELLOW}Consider running the development workflow to address issues.${NC}"
fi

echo -e "\n${GREEN}--- Atlas Session Complete ---${NC}" 