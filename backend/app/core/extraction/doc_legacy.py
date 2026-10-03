"""Minimal reader for legacy binary Word (.doc): returns the document text (Word 97-2003 piece table), with table cell
and row marks (\\x07) preserved so tables can be rebuilt. No external converter needed (LibreOffice Writer is not
guaranteed to exist in the deployment image). Read-only; the file is never modified."""
import io
import struct


class NotAWordDocument(ValueError):
    pass


def read_doc_text(content: bytes) -> str:
    import olefile
    if not olefile.isOleFile(content):
        raise NotAWordDocument("Not an OLE (.doc) file")
    o = olefile.OleFileIO(io.BytesIO(content))
    try:
        if not o.exists("WordDocument"):
            raise NotAWordDocument("No WordDocument stream")
        wd = o.openstream("WordDocument").read()
        flags = struct.unpack_from("<H", wd, 0x0A)[0]
        table = o.openstream("1Table" if flags & 0x0200 else "0Table").read()
    finally:
        o.close()
    fc_clx, lcb_clx = struct.unpack_from("<II", wd, 0x01A2)
    clx = table[fc_clx:fc_clx + lcb_clx]
    i = 0
    while i < len(clx) and clx[i] == 1:  # skip grpprl entries
        i += 3 + struct.unpack_from("<H", clx, i + 1)[0]
    if i >= len(clx) or clx[i] != 2:
        raise NotAWordDocument("Piece table not found")
    n = struct.unpack_from("<I", clx, i + 1)[0]
    plc = clx[i + 5:i + 5 + n]
    count = (n - 4) // 12
    cps = struct.unpack_from("<%dI" % (count + 1), plc, 0)
    parts = []
    for k in range(count):
        pcd = plc[4 * (count + 1) + 8 * k:4 * (count + 1) + 8 * k + 8]
        fc = struct.unpack_from("<I", pcd, 2)[0]
        compressed = bool(fc & 0x40000000)
        fc &= 0x3FFFFFFF
        nch = cps[k + 1] - cps[k]
        if compressed:
            parts.append(wd[fc // 2:fc // 2 + nch].decode("cp1256", errors="replace"))
        else:
            parts.append(wd[fc:fc + 2 * nch].decode("utf-16-le", errors="replace"))
    return "".join(parts)
