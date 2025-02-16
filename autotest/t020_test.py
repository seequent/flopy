# Test modflow write adn run
import numpy as np

try:
    import matplotlib.pyplot as plt

    # if os.getenv('TRAVIS'):  # are we running https://travis-ci.org/ automated tests ?
    #     matplotlib.use('Agg')  # Force matplotlib  not to use any Xwindows backend
except:
    plt = None


def analyticalWaterTableSolution(h1, h2, z, R, K, L, x):
    h = np.zeros((x.shape[0]), float)
    b1 = h1 - z
    b2 = h2 - z
    h = (
        np.sqrt(
            b1 ** 2 - (x / L) * (b1 ** 2 - b2 ** 2) + (R * x / K) * (L - x)
        )
        + z
    )
    return h


def test_mfnwt_run():
    import os
    import flopy

    exe_name = "mfnwt"
    exe = flopy.which(exe_name)

    if exe is None:
        print(f"Specified executable {exe_name} does not exist in path")
        return

    modelname = "watertable"
    model_ws = os.path.join("temp", "t020")
    if not os.path.exists(model_ws):
        os.makedirs(model_ws)

    # model dimensions
    nlay, nrow, ncol = 1, 1, 100

    # cell spacing
    delr = 50.0
    delc = 1.0

    # domain length
    L = 5000.0

    # boundary heads
    h1 = 20.0
    h2 = 11.0

    # ibound
    ibound = np.ones((nlay, nrow, ncol), dtype=int)

    # starting heads
    strt = np.zeros((nlay, nrow, ncol), dtype=float)
    strt[0, 0, 0] = h1
    strt[0, 0, -1] = h2

    # top of the aquifer
    top = 25.0

    # bottom of the aquifer
    botm = 0.0

    # hydraulic conductivity
    hk = 50.0

    # location of cell centroids
    x = np.arange(0.0, L, delr) + (delr / 2.0)

    # location of cell edges
    xa = np.arange(0, L + delr, delr)

    # recharge rate
    rchrate = 0.001

    # calculate the head at the cell centroids using the analytical solution function
    hac = analyticalWaterTableSolution(h1, h2, botm, rchrate, hk, L, x)

    # calculate the head at the cell edges using the analytical solution function
    ha = analyticalWaterTableSolution(h1, h2, botm, rchrate, hk, L, xa)

    # ghbs
    # ghb conductance
    b1, b2 = 0.5 * (h1 + hac[0]), 0.5 * (h2 + hac[-1])
    c1, c2 = hk * b1 * delc / (0.5 * delr), hk * b2 * delc / (0.5 * delr)
    # dtype
    ghb_dtype = flopy.modflow.ModflowGhb.get_default_dtype()

    # build ghb recarray
    stress_period_data = np.zeros((2), dtype=ghb_dtype)
    stress_period_data = stress_period_data.view(np.recarray)

    # fill ghb recarray
    stress_period_data[0] = (0, 0, 0, h1, c1)
    stress_period_data[1] = (0, 0, ncol - 1, h2, c2)

    mf = flopy.modflow.Modflow(
        modelname=modelname, exe_name=exe, model_ws=model_ws, version="mfnwt"
    )
    dis = flopy.modflow.ModflowDis(
        mf,
        nlay,
        nrow,
        ncol,
        delr=delr,
        delc=delc,
        top=top,
        botm=botm,
        perlen=1,
        nstp=1,
        steady=True,
    )
    bas = flopy.modflow.ModflowBas(mf, ibound=ibound, strt=strt)
    lpf = flopy.modflow.ModflowUpw(mf, hk=hk, laytyp=1)
    ghb = flopy.modflow.ModflowGhb(mf, stress_period_data=stress_period_data)
    rch = flopy.modflow.ModflowRch(mf, rech=rchrate, nrchop=1)
    oc = flopy.modflow.ModflowOc(mf)
    nwt = flopy.modflow.ModflowNwt(mf)
    mf.write_input()

    # remove existing heads results, if necessary
    try:
        os.remove(os.path.join(model_ws, f"{modelname}.hds"))
    except:
        pass
    # run existing model
    mf.run_model()

    # Read the simulated MODFLOW-2005 model results
    # Create the headfile object
    headfile = os.path.join(model_ws, f"{modelname}.hds")
    headobj = flopy.utils.HeadFile(headfile, precision="single")
    times = headobj.get_times()
    head = headobj.get_data(totim=times[-1])

    # Plot the results
    if plt is not None:
        fig = plt.figure(figsize=(16, 6))

        ax = fig.add_subplot(1, 3, 1)
        ax.plot(xa, ha, linewidth=8, color="0.5", label="analytical solution")
        ax.plot(x, head[0, 0, :], color="red", label="MODFLOW-NWT")
        leg = ax.legend(loc="lower left")
        leg.draw_frame(False)
        ax.set_xlabel("Horizontal distance, in m")
        ax.set_ylabel("Head, in m")

        ax = fig.add_subplot(1, 3, 2)
        ax.plot(x, head[0, 0, :] - hac, linewidth=1, color="blue")
        ax.set_xlabel("Horizontal distance, in m")
        ax.set_ylabel("Error, in m")

        ax = fig.add_subplot(1, 3, 3)
        ax.plot(
            x, 100.0 * (head[0, 0, :] - hac) / hac, linewidth=1, color="blue"
        )
        ax.set_xlabel("Horizontal distance, in m")
        ax.set_ylabel("Percent Error")

        fig.savefig(os.path.join(model_ws, f"{modelname}.png"))

    return


def test_irch():
    import os
    import flopy

    org_model_ws = os.path.join(
        "..", "examples", "data", "freyberg_multilayer_transient"
    )
    nam_file = "freyberg.nam"
    m = flopy.modflow.Modflow.load(
        nam_file,
        model_ws=org_model_ws,
        check=False,
        forgive=False,
        verbose=True,
    )
    irch = {}
    for kper in range(m.nper):
        arr = np.random.randint(0, m.nlay, size=(m.nrow, m.ncol))
        irch[kper] = arr

    m.remove_package("RCH")
    flopy.modflow.ModflowRch(m, rech=0.1, irch=irch, nrchop=2)

    for kper in range(m.nper):
        arr = irch[kper]
        aarr = m.rch.irch[kper].array
        d = arr - aarr
        assert np.abs(d).sum() == 0

    new_model_ws = "temp"
    m.change_model_ws(new_model_ws)
    m.write_input()
    mm = flopy.modflow.Modflow.load(
        nam_file, model_ws="temp", forgive=False, verbose=True, check=False
    )
    for kper in range(m.nper):
        arr = irch[kper]
        aarr = mm.rch.irch[kper].array
        d = arr - aarr
        assert np.abs(d).sum() == 0


if __name__ == "__main__":
    # test_mfnwt_run()
    test_irch()
