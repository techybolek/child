# Chore: Remove test_failed.py Auto-Generation

## Chore Description
Remove the automatic generation of `test_failed.py` when evaluation stops on failure. This feature is obsolete because the evaluation system now has checkpoint and resume functionality that allows surgical re-evaluation of failed questions. The checkpoint system saves progress and excludes failed questions, making the auto-generated debug script unnecessary.

**Current Behavior**: When a question scores below threshold (default: 60/100), the evaluation:
1. Saves checkpoint (excluding the failed question)
2. Auto-generates `test_failed.py` with the failed question
3. Stops execution

**Desired Behavior**: When a question scores below threshold:
1. Saves checkpoint (excluding the failed question)
2. Stops execution with clear failure message
3. Developer uses `--resume` flag to re-evaluate from the failed question

## Relevant Files
Use these files to resolve the chore:

- **evaluation/batch_evaluator.py** (lines 239-306)
  - Contains `_generate_test_file()` method that creates the auto-generated file
  - Contains `_print_failure_and_stop()` method (line 228) that calls `_generate_test_file()`
  - Needs removal of test file generation logic

- **evaluation/batch_evaluator.py** (line 228)
  - Call to `_generate_test_file()` in the failure handler
  - Needs to be removed

- **SPECS/evaluation_system.md** (lines 62-90)
  - Documents the "Auto-Generated test_failed.py" feature section
  - Needs update to remove references and explain resume workflow instead

- **SPECS/contextual_retrieval_implementation.md**
  - References `test_failed.py` usage
  - Needs update to show resume workflow

- **SPECS/contextual_retrieval_status.md**
  - References `test_failed.py` usage
  - Needs update to show resume workflow

- **SPECS/contextual_embedding_guide.md**
  - References `test_failed.py` usage
  - Needs update to show resume workflow

- **SPECS/README.md**
  - May reference the feature
  - Needs review and potential update

- **CLAUDE.md** (root)
  - Main project documentation that references test_failed.py
  - Needs update to remove references

### New Files
None required - this is a removal chore.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Remove Auto-Generation Code from BatchEvaluator
- Delete the `_generate_test_file()` method (lines 239-306 in `evaluation/batch_evaluator.py`)
- Remove the call to `self._generate_test_file(qa, chatbot_response, scores)` from `_print_failure_and_stop()` method (line 228)
- Update the failure message in `_print_failure_and_stop()` to guide users to use `--resume` instead
- Ensure the checkpoint save logic remains intact (critical for resume functionality)

### Step 2: Update Failure Message
- Modify `_print_failure_and_stop()` to output clear instructions for using `--resume`
- Message should explain:
  - Checkpoint was saved with progress up to (but not including) the failed question
  - Use `python -m evaluation.run_evaluation --resume` to continue from the failed question
  - Optionally use `--resume-limit N` to re-evaluate only N questions starting from failure
  - The failed question will be re-evaluated on resume

### Step 3: Update SPECS/evaluation_system.md
- Remove the "Auto-Generated test_failed.py" section (lines 62-90)
- Replace with a "Resume After Failure" section explaining:
  - How checkpoint system works on failure
  - How to use `--resume` flag
  - How to use `--resume-limit` for targeted re-evaluation
  - Example workflow for fixing and re-evaluating failed questions
- Update the "Stop-on-Fail Behavior" section to remove references to test_failed.py generation
- Update the "Typical Workflow" section to use resume instead of test_failed.py

### Step 4: Update SPECS/contextual_retrieval_implementation.md
- Find all references to `test_failed.py`
- Replace with resume workflow examples
- Update any workflow diagrams or examples

### Step 5: Update SPECS/contextual_retrieval_status.md
- Find all references to `test_failed.py`
- Replace with resume workflow examples
- Ensure consistency with evaluation_system.md updates

### Step 6: Update SPECS/contextual_embedding_guide.md
- Find all references to `test_failed.py`
- Replace with resume workflow examples
- Ensure consistency with evaluation_system.md updates

### Step 7: Update SPECS/README.md
- Search for any references to `test_failed.py`
- Remove or update references to match new resume workflow
- Ensure documentation index is consistent

### Step 8: Update CLAUDE.md (Root Documentation)
- Search for any references to `test_failed.py`
- Remove references from "Output Files" section
- Update "Testing Approach" or workflow sections to use resume functionality
- Ensure consistency with SPECS updates

### Step 9: Clean Up Existing test_failed.py (Optional Manual Step)
- Note: The existing auto-generated `test_failed.py` in the project root can be manually deleted
- Add to `.gitignore` if not already present (verify it's in .gitignore)
- Document in completion notes that developers should manually delete their local copy

### Step 10: Run Validation Commands
- Execute all validation commands listed below to ensure zero regressions
- Verify evaluation still stops on failure and saves checkpoint
- Verify resume functionality works correctly
- Verify all tests pass

## Validation Commands
Execute every command to validate the chore is complete with zero regressions.

- `python -m pytest evaluation/test_batch_evaluator.py -v` - Run evaluation tests (if they exist)
- `python -m evaluation.run_evaluation --test --limit 1` - Test basic evaluation execution
- `python -c "from evaluation.batch_evaluator import BatchEvaluator; import inspect; assert '_generate_test_file' not in dir(BatchEvaluator), 'Method still exists!'; print('✓ Auto-generation method removed')"` - Verify method removal
- `grep -r "test_failed.py" SPECS/ CLAUDE.md --exclude-dir=.git` - Verify documentation updated (should only show historical context if any, not usage instructions)
- `python -m evaluation.run_evaluation --help` - Verify help text is accurate and mentions --resume
- `ls test_failed.py 2>/dev/null && echo "⚠ Manual cleanup needed: delete test_failed.py" || echo "✓ No test_failed.py in root"` - Check if cleanup needed

## Notes

### Critical Considerations
- **DO NOT remove checkpoint save logic** - This is essential for the resume functionality
- **DO NOT change checkpoint behavior** - Failed questions should still be excluded from checkpoint
- The checkpoint system already provides the exact functionality that test_failed.py was meant to provide
- Resume workflow is superior because:
  - No need to maintain two separate evaluation paths (full pipeline vs. test_failed.py)
  - Checkpoint automatically tracks which question failed
  - `--resume-limit` allows targeted re-evaluation (same benefit as test_failed.py but integrated)
  - Consistent with the rest of the evaluation architecture

### Resume Workflow Benefits
- **Before (with test_failed.py)**:
  1. Evaluation fails on Q15
  2. test_failed.py generated
  3. Developer runs `python test_failed.py` to debug Q15
  4. Developer must manually resume evaluation with `--resume`

- **After (checkpoint only)**:
  1. Evaluation fails on Q15
  2. Checkpoint saved (up to Q14)
  3. Developer runs `python -m evaluation.run_evaluation --resume --resume-limit 1` to re-evaluate just Q15
  4. OR runs `--resume` to continue from Q15 onwards

### Documentation Philosophy
- Emphasize the checkpoint/resume workflow as the primary debugging method
- Show examples of `--resume` and `--resume-limit` usage
- Explain that failed questions are automatically excluded from checkpoint and will be re-evaluated on resume
- Keep documentation consistent across all SPECS files

### Backward Compatibility
- Existing checkpoints will continue to work
- No changes to checkpoint format or resume logic
- Only removing the auto-generation side effect
- Developers with existing test_failed.py can continue using it manually, but it won't be regenerated

### Testing Strategy
- Verify evaluation can still detect failures (threshold check)
- Verify checkpoint saves correctly on failure
- Verify resume works after failure
- Verify --resume-limit works for surgical re-evaluation
- Ensure no references to _generate_test_file remain in codebase
