# Test binary and formatted data readers
import os
import shutil
import numpy as np
import flopy
from nose.tools import assert_raises

cpth = os.path.join("temp", "t017")
# delete the directory if it exists
if os.path.isdir(cpth):
    shutil.rmtree(cpth)
os.makedirs(cpth)


def test_formattedfile_read():

    h = flopy.utils.FormattedHeadFile(
        os.path.join("..", "examples", "data", "mf2005_test", "test1tr.githds")
    )
    assert isinstance(h, flopy.utils.FormattedHeadFile)

    times = h.get_times()
    assert np.isclose(times[0], 1577880064.0)

    kstpkper = h.get_kstpkper()
    assert kstpkper[0] == (49, 0), "kstpkper[0] != (49, 0)"

    h0 = h.get_data(totim=times[0])
    h1 = h.get_data(kstpkper=kstpkper[0])
    h2 = h.get_data(idx=0)
    assert np.array_equal(
        h0, h1
    ), "formatted head read using totim != head read using kstpkper"
    assert np.array_equal(
        h0, h2
    ), "formatted head read using totim != head read using idx"

    ts = h.get_ts((0, 7, 5))
    expected = 944.487
    assert np.isclose(
        ts[0, 1], expected, 1e-6
    ), f"time series value ({ts[0, 1]}) != {expected}"
    h.close()

    # Check error when reading empty file
    fname = os.path.join(cpth, "empty.githds")
    with open(fname, "w"):
        pass
    with assert_raises(ValueError):
        flopy.utils.FormattedHeadFile(fname)

    return


def test_binaryfile_read():

    h = flopy.utils.HeadFile(
        os.path.join("..", "examples", "data", "freyberg", "freyberg.githds")
    )
    assert isinstance(h, flopy.utils.HeadFile)

    times = h.get_times()
    assert np.isclose(times[0], 10.0), f"times[0] != {times[0]}"

    kstpkper = h.get_kstpkper()
    assert kstpkper[0] == (0, 0), "kstpkper[0] != (0, 0)"

    h0 = h.get_data(totim=times[0])
    h1 = h.get_data(kstpkper=kstpkper[0])
    h2 = h.get_data(idx=0)
    assert np.array_equal(
        h0, h1
    ), "binary head read using totim != head read using kstpkper"
    assert np.array_equal(
        h0, h2
    ), "binary head read using totim != head read using idx"

    ts = h.get_ts((0, 7, 5))
    expected = 26.00697135925293
    assert np.isclose(
        ts[0, 1], expected
    ), f"time series value ({ts[0, 1]}) != {expected}"
    h.close()

    # Check error when reading empty file
    fname = os.path.join(cpth, "empty.githds")
    with open(fname, "w"):
        pass
    with assert_raises(ValueError):
        flopy.utils.HeadFile(fname)
    with assert_raises(ValueError):
        flopy.utils.HeadFile(fname, "head", "single")

    return


def test_binaryfile_read_context():
    hds_path = os.path.join(
        "..", "examples", "data", "freyberg", "freyberg.githds"
    )
    with flopy.utils.HeadFile(hds_path) as h:
        data = h.get_data()
        assert data.max() > 0, data.max()
        assert not h.file.closed
    assert h.file.closed

    with assert_raises(ValueError) as e:
        h.get_data()
    assert str(e.exception) == "seek of closed file", str(e.exception)


def test_cellbudgetfile_read_context():
    cbc_path = os.path.join(
        "..", "examples", "data", "mf2005_test", "mnw1.gitcbc"
    )
    with flopy.utils.CellBudgetFile(cbc_path) as v:
        data = v.get_data(text="DRAINS")[0]
        assert data.min() < 0, data.min()
        assert not v.file.closed
    assert v.file.closed

    with assert_raises(ValueError) as e:
        v.get_data(text="DRAINS")
    assert str(e.exception) == "seek of closed file", str(e.exception)


def test_cellbudgetfile_read():

    v = flopy.utils.CellBudgetFile(
        os.path.join("..", "examples", "data", "mf2005_test", "mnw1.gitcbc")
    )
    assert isinstance(v, flopy.utils.CellBudgetFile)

    kstpkper = v.get_kstpkper()
    assert len(kstpkper) == 5, "length of kstpkper != 5"

    records = v.get_unique_record_names()
    idx = 0
    for t in kstpkper:
        for record in records:
            t0 = v.get_data(kstpkper=t, text=record, full3D=True)[0]
            t1 = v.get_data(idx=idx, text=record, full3D=True)[0]
            assert np.array_equal(
                t0, t1
            ), "binary budget item {0} read using kstpkper != binary budget item {0} read using idx".format(
                record
            )
            idx += 1
    v.close()
    return


def test_cellbudgetfile_position():

    fpth = os.path.join(
        "..", "examples", "data", "zonbud_examples", "freyberg.gitcbc"
    )
    v = flopy.utils.CellBudgetFile(fpth)
    assert isinstance(v, flopy.utils.CellBudgetFile)

    # starting position of data
    idx = 8767
    ipos = v.get_position(idx)
    ival = 50235424
    assert ipos == ival, f"position of index 8767 != {ival}"

    ipos = v.get_position(idx, header=True)
    ival = 50235372
    assert ipos == ival, f"position of index 8767 header != {ival}"

    cbcd = []
    for i in range(idx, v.get_nrecords()):
        cbcd.append(v.get_data(i)[0])
    v.close()

    # write the last entry as a new binary file
    fin = open(fpth, "rb")
    fin.seek(ipos)
    length = os.path.getsize(fpth) - ipos

    buffsize = 32
    opth = os.path.join(cpth, "end.cbc")
    with open(opth, "wb") as fout:
        while length:
            chunk = min(buffsize, length)
            data = fin.read(chunk)
            fout.write(data)
            length -= chunk
    fin.close()

    v2 = flopy.utils.CellBudgetFile(opth, verbose=True)

    try:
        v2.list_records()
    except:
        assert False, f"could not list records on {opth}"

    names = v2.get_unique_record_names(decode=True)

    cbcd2 = []
    for i in range(0, v2.get_nrecords()):
        cbcd2.append(v2.get_data(i)[0])
    v2.close()

    for i, (d1, d2) in enumerate(zip(cbcd, cbcd2)):
        msg = f"{names[i].rstrip()} data from slice is not identical"
        assert np.array_equal(d1, d2), msg

    # Check error when reading empty file
    fname = os.path.join(cpth, "empty.gitcbc")
    with open(fname, "w"):
        pass
    with assert_raises(ValueError):
        flopy.utils.CellBudgetFile(fname)

    return


def test_cellbudgetfile_readrecord():

    cbc_fname = os.path.join(
        "..", "examples", "data", "mf2005_test", "test1tr.gitcbc"
    )
    v = flopy.utils.CellBudgetFile(cbc_fname)
    assert isinstance(v, flopy.utils.CellBudgetFile)

    kstpkper = v.get_kstpkper()
    assert len(kstpkper) == 30, "length of kstpkper != 30"

    with assert_raises(TypeError) as e:
        v.get_data()
    assert str(e.exception).startswith(
        "get_data() missing 1 required argument"
    ), str(e.exception)

    t = v.get_data(text="STREAM LEAKAGE")
    assert len(t) == 30, "length of stream leakage data != 30"
    assert (
        t[0].shape[0] == 36
    ), "sfr budget data does not have 36 reach entries"

    t = v.get_data(text="STREAM LEAKAGE", full3D=True)
    assert t[0].shape == (1, 15, 10), (
        "3D sfr budget data does not have correct shape (1, 15,10) - "
        "returned shape {}".format(t[0].shape)
    )

    for kk in kstpkper:
        t = v.get_data(kstpkper=kk, text="STREAM LEAKAGE", full3D=True)[0]
        assert t.shape == (1, 15, 10), (
            "3D sfr budget data for kstpkper {} "
            "does not have correct shape (1, 15,10) - "
            "returned shape {}".format(kk, t[0].shape)
        )

    idx = v.get_indices()
    assert idx is None, "get_indices() without record did not return None"

    records = v.get_unique_record_names()
    for record in records:
        indices = v.get_indices(text=record.strip())
        for idx, kk in enumerate(kstpkper):
            t0 = v.get_data(kstpkper=kk, text=record.strip())[0]
            t1 = v.get_data(idx=indices[idx], text=record)[0]
            assert np.array_equal(
                t0, t1
            ), "binary budget item {0} read using kstpkper != binary budget item {0} read using idx".format(
                record
            )

    # idx can be either an int or a list of ints
    s9 = v.get_data(idx=9)
    assert len(s9) == 1
    s09 = v.get_data(idx=[0, 9])
    assert len(s09) == 2
    assert (s09[1] == s9).all()

    v.close()
    return


def test_cellbudgetfile_readrecord_waux():

    cbc_fname = os.path.join(
        "..", "examples", "data", "mf2005_test", "test1tr.gitcbc"
    )
    v = flopy.utils.CellBudgetFile(cbc_fname)
    assert isinstance(v, flopy.utils.CellBudgetFile)

    kstpkper = v.get_kstpkper()
    assert len(kstpkper) == 30, "length of kstpkper != 30"

    t = v.get_data(text="WELLS")
    assert len(t) == 30, "length of well data != 30"
    assert t[0].shape[0] == 10, "wel budget data does not have 10 well entries"

    t = v.get_data(text="WELLS", full3D=True)
    assert t[0].shape == (1, 15, 10), (
        "3D wel budget data does not have correct shape (1, 15,10) - "
        "returned shape {}".format(t[0].shape)
    )

    for kk in kstpkper:
        t = v.get_data(kstpkper=kk, text="wells", full3D=True)[0]
        assert t.shape == (1, 15, 10), (
            "3D wel budget data for kstpkper {} "
            "does not have correct shape (1, 15,10) - "
            "returned shape {}".format(kk, t[0].shape)
        )

    idx = v.get_indices()
    assert idx is None, "get_indices() without record did not return None"

    records = v.get_unique_record_names()
    for record in records:
        indices = v.get_indices(text=record.strip())
        for idx, kk in enumerate(kstpkper):
            t0 = v.get_data(kstpkper=kk, text=record.strip())[0]
            t1 = v.get_data(idx=indices[idx], text=record)[0]
            assert np.array_equal(
                t0, t1
            ), "binary budget item {0} read using kstpkper != binary budget item {0} read using idx".format(
                record
            )
    v.close()
    return


def test_binaryfile_writeread():

    pth = os.path.join("..", "examples", "data", "nwt_test")
    model = "Pr3_MFNWT_lower.nam"
    ml = flopy.modflow.Modflow.load(model, version="mfnwt", model_ws=pth)
    # change the model work space
    ml.change_model_ws(os.path.join("temp", "t017"))
    #
    ncol = ml.dis.ncol
    nrow = ml.dis.nrow
    text = "head"
    # write a double precision head file
    precision = "double"
    pertim = ml.dis.perlen.array[0].astype(np.float64)
    header = flopy.utils.BinaryHeader.create(
        bintype=text,
        precision=precision,
        text=text,
        nrow=nrow,
        ncol=ncol,
        ilay=1,
        pertim=pertim,
        totim=pertim,
        kstp=1,
        kper=1,
    )
    b = ml.dis.botm.array[0, :, :].astype(np.float64)
    pth = os.path.join("temp", "t017", "bottom.hds")
    flopy.utils.Util2d.write_bin(b.shape, pth, b, header_data=header)

    bo = flopy.utils.HeadFile(pth, precision=precision)
    times = bo.get_times()
    errmsg = "double precision binary totim read is not equal to totim written"
    assert times[0] == pertim, errmsg
    kstpkper = bo.get_kstpkper()
    errmsg = "kstp, kper read is not equal to kstp, kper written"
    assert kstpkper[0] == (0, 0), errmsg
    br = bo.get_data()
    errmsg = "double precision binary data read is not equal to data written"
    assert np.allclose(b, br), errmsg

    # write a single precision head file
    precision = "single"
    pertim = ml.dis.perlen.array[0].astype(np.float32)
    header = flopy.utils.BinaryHeader.create(
        bintype=text,
        precision=precision,
        text=text,
        nrow=nrow,
        ncol=ncol,
        ilay=1,
        pertim=pertim,
        totim=pertim,
        kstp=1,
        kper=1,
    )
    b = ml.dis.botm.array[0, :, :].astype(np.float32)
    pth = os.path.join("temp", "t017", "bottom_single.hds")
    flopy.utils.Util2d.write_bin(b.shape, pth, b, header_data=header)

    bo = flopy.utils.HeadFile(pth, precision=precision)
    times = bo.get_times()
    errmsg = "single precision binary totim read is not equal to totim written"
    assert times[0] == pertim, errmsg
    kstpkper = bo.get_kstpkper()
    errmsg = "kstp, kper read is not equal to kstp, kper written"
    assert kstpkper[0] == (0, 0), errmsg
    br = bo.get_data()
    errmsg = "singleprecision binary data read is not equal to data written"
    assert np.allclose(b, br), errmsg

    return


if __name__ == "__main__":
    test_cellbudgetfile_position()
    test_binaryfile_writeread()
    test_formattedfile_read()
    test_binaryfile_read()
    test_cellbudgetfile_read()
    test_cellbudgetfile_readrecord()
    test_cellbudgetfile_readrecord_waux()
