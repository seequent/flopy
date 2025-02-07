"""
Test loading and preserving existing unit numbers
"""
import os
import shutil

import flopy

pth = os.path.join("..", "examples", "data", "mf2005_test")
cpth = os.path.join("temp", "t036")

# make the directory if it does not exist
if not os.path.isdir(cpth):
    os.makedirs(cpth)


def test_uzf_unit_numbers():
    exe_name = "mf2005"
    v = flopy.which(exe_name)

    run = True
    if v is None:
        run = False

    mfnam = "UZFtest2.nam"
    pt = os.path.join("..", "examples", "data", "uzf_examples")

    # copy files
    try:
        import pymake

        lpth = os.path.join(cpth, os.path.splitext(mfnam)[0])
        apth = os.path.join(lpth, "flopy")
        compth = lpth
        pymake.setup(os.path.join(pt, mfnam), lpth)
    except:
        run = False
        lpth = pth
        apth = cpth
        compth = cpth

    m = flopy.modflow.Modflow.load(
        mfnam, verbose=True, model_ws=lpth, forgive=False, exe_name=exe_name
    )
    assert m.load_fail is False, "failed to load all packages"

    # reset the oc file
    m.remove_package("OC")
    output = ["save head", "print budget"]
    spd = {}
    for iper in range(1, m.dis.nper):
        for istp in [0, 4, 9, 14]:
            spd[(iper, istp)] = output
    spd[(0, 0)] = output
    spd[(1, 1)] = output
    spd[(1, 2)] = output
    spd[(1, 3)] = output
    oc = flopy.modflow.ModflowOc(m, stress_period_data=spd)
    oc.write_file()

    if run:
        try:
            success, buff = m.run_model(silent=False)
        except:
            success = False
        assert success, "base model run did not terminate successfully"
        fn0 = os.path.join(lpth, mfnam)

    # change uzf iuzfcb2 and add binary uzf output file
    m.uzf.iuzfcb2 = 61
    m.add_output_file(m.uzf.iuzfcb2, extension="uzfcb2.bin", package="UZF")

    # change the model work space
    m.change_model_ws(apth, reset_external=True)

    # rewrite files
    m.write_input()

    # run and compare the output files
    if run:
        try:
            success, buff = m.run_model(silent=False)
        except:
            success = False
        assert success, "new model run did not terminate successfully"
        fn1 = os.path.join(apth, mfnam)

    # compare budget terms
    if run:
        fsum = os.path.join(compth, f"{os.path.splitext(mfnam)[0]}.budget.out")
        try:
            success = pymake.compare_budget(
                fn0, fn1, max_incpd=0.1, max_cumpd=0.1, outfile=fsum
            )
        except:
            success = False
            print("could not perform ls" "budget comparison")

        assert success, "budget comparison failure"

    # clean up
    shutil.rmtree(lpth)

    return


def test_unitnums_load_and_write():
    exe_name = "mf2005"
    v = flopy.which(exe_name)

    run = True
    if v is None:
        run = False

    mfnam = "testsfr2_tab.nam"

    # copy files
    try:
        import pymake

        lpth = os.path.join(cpth, os.path.splitext(mfnam)[0])
        apth = os.path.join(lpth, "flopy")
        compth = lpth
        pymake.setup(os.path.join(pth, mfnam), lpth)
    except:
        run = False
        lpth = pth
        apth = cpth
        compth = cpth

    m = flopy.modflow.Modflow.load(
        mfnam, verbose=True, model_ws=lpth, exe_name=exe_name
    )
    assert m.load_fail is False, "failed to load all packages"

    msg = (
        "modflow-2005 testsfr2_tab does not have "
        "1 layer, 7 rows, and 100 columns"
    )
    v = (m.nlay, m.nrow, m.ncol, m.nper)
    assert v == (1, 7, 100, 50), msg

    if run:
        try:
            success, buff = m.run_model(silent=False)
        except:
            success = False
        assert success, "base model run did not terminate successfully"
        fn0 = os.path.join(lpth, mfnam)

    # rewrite files
    m.change_model_ws(apth, reset_external=True)
    m.write_input()
    if run:
        try:
            success, buff = m.run_model(silent=False)
        except:
            success = False
        assert success, "base model run did not terminate successfully"
        fn1 = os.path.join(apth, mfnam)

    if run:
        fsum = os.path.join(compth, f"{os.path.splitext(mfnam)[0]}.budget.out")
        try:
            success = pymake.compare_budget(
                fn0, fn1, max_incpd=0.1, max_cumpd=0.1, outfile=fsum
            )
        except:
            success = False
            print("could not perform ls" "budget comparison")

        assert success, "budget comparison failure"

    # clean up
    shutil.rmtree(lpth)

    return


if __name__ == "__main__":
    test_uzf_unit_numbers()
    test_unitnums_load_and_write()
