ROOT_CAUSE_HYPOTHESIS: cycle 02 failed in the new evidence observer, which attempted to copy Nav2's temporary SDF before concurrent xacro generation completed.
EVIDENCE_SUPPORTING_IT: server argv names the expected temporary path; no world file existed at its immediate first observation. Owned processes were cleaned, protected hashes unchanged.
SMALLEST_CHANGE: bounded file-existence wait in observer only; no change to runner, world augmentation, server or GUI.
EXPECTED_RESULT: capture the generated SDF then proceed to live scene / GUI / mission gates.
