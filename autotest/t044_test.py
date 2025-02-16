"""
Test the observation process load and write
"""
import os
import shutil
import filecmp
import flopy

try:
    import pymake
except ImportError:
    print("could not import pymake")
    pymake = False

path = os.path.join("..", "examples", "data", "pcgn_test")
cpth = os.path.join("temp", "t044")
# delete the directory if it exists
if os.path.isdir(cpth):
    shutil.rmtree(cpth)
# make the directory
os.makedirs(cpth)

mf_items = ["twri.nam", "MNW2.nam"]
pths = []
for val in mf_items:
    pths.append(path)


def load_and_write_pcgn(mfnam, pth):
    """
    test044 load and write of MODFLOW-2005 PCGN example problem
    """
    exe_name = "mf2005"
    v = flopy.which(exe_name)

    if pymake:
        run = v is not None
        lpth = os.path.join(cpth, os.path.splitext(mfnam)[0])
        apth = os.path.join(lpth, "flopy")
        compth = lpth
        pymake.setup(os.path.join(pth, mfnam), lpth)
    else:
        run = False
        lpth = pth
        apth = cpth
        compth = cpth

    m = flopy.modflow.Modflow.load(
        mfnam, model_ws=lpth, verbose=True, exe_name=exe_name
    )
    assert m.load_fail is False
    if mfnam in ["twri.nam"]:  # update this list for fixed models
        assert m.free_format_input is False
    else:
        assert m.free_format_input is True

    if run:
        try:
            success, buff = m.run_model(silent=False)
        except:
            success = False
        assert success, "base model run did not terminate successfully"
        fn0 = os.path.join(lpth, mfnam)

    # rewrite files
    m.change_model_ws(apth)
    m.write_input()
    if run:
        try:
            success, buff = m.run_model(silent=False)
        except:
            success = False
        assert success, "new model run did not terminate successfully"
        fn1 = os.path.join(apth, mfnam)

    if run:
        fsum = os.path.join(compth, f"{os.path.splitext(mfnam)[0]}.head.out")
        success = False
        try:
            success = pymake.compare_heads(fn0, fn1, outfile=fsum, htol=0.005)
        except:
            success = False
            print("could not perform head comparison")

        assert success, "head comparison failure"

        fsum = os.path.join(compth, f"{os.path.splitext(mfnam)[0]}.budget.out")
        success = False
        try:
            success = pymake.compare_budget(
                fn0, fn1, max_incpd=0.1, max_cumpd=0.1, outfile=fsum
            )
        except:
            success = False
            print("could not perform budget comparison")

        assert success, "budget comparison failure"

    return


def test_mf2005pcgnload():
    for namfile, pth in zip(mf_items, pths):
        yield load_and_write_pcgn, namfile, pth
    return


if __name__ == "__main__":
    # for namfile, pth in zip(mf_items, pths):
    #    load_and_write_pcgn(namfile, pth)
    load_and_write_pcgn(mf_items[1], pths[1])
