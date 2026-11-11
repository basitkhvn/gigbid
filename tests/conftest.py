import os
import tempfile

# isolate every test run: own state dir, offline model profile, generous limiters
os.environ["GIGBID_STATE_DIR"] = tempfile.mkdtemp(prefix="gb_test_")
os.environ["MODEL_PROFILE"] = "offline"
os.environ["MARKETPLACE_RATE_PER_MIN"] = "100000"
os.environ["GIGSIM_RATE_LIMIT"] = "100000"
os.environ["GIGSIM_CONNECTS"] = "100000"
