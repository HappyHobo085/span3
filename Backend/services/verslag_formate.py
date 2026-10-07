"""Skryf 'n verslag-oorsig (services/verslag_service.bou_oorsig) uit as 'n lêer.

Formate:
- xlsx: een blad per afdeling (Kampus/Koshuis/Events, of Klas), met Excel-grafieke.
- pdf:  liggende A4 met grafieke (reportlab).
- docx: Word-dokument; grafieke word as verdelingstabelle gewys (python-docx).
- txt:  gewone teks met vaste-breedte tabelle.

Die oorsig is formaat-neutraal: elke afdeling het kernsyfers, insigte,
grafieke (sirkel/balk/lyn) en tabelle met getipeerde kolomme.
"""

from __future__ import annotations

import io
from datetime import date, datetime
from typing import Callable, Optional
from xml.sax.saxutils import escape

from fastapi import HTTPException

from services.verslag_service import DATUM, DATUMTYD, GETAL, LAE_BYWONING, PERSENT

MEDIA_TIPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain; charset=utf-8",
}

# PDF en Word bly leesbaar: baie groot tabelle word afgekap (Excel/teks kry alles).
MAKS_DOKUMENT_RYE = 2000

# Reekskleure vir drukwerk/ligte agtergrond (dieselfde as die webwerf se ligte tema);
# die derde kleur is die dowwe "res"-kategorie (bv. "Nog nooit gescan").
_KLEURE = ["0077A8", "6D52F4", "B8BFCC"]
_NAVY = "1F3A5F"


# --------------------------------------------------------------------------- #
# Gedeelde formatering
# --------------------------------------------------------------------------- #

def formateer(waarde, formaat: str, leeg: str = "") -> str:
    if waarde is None or waarde == "":
        return leeg
    if formaat == PERSENT:
        return f"{waarde:.0%}"
    if formaat == DATUMTYD and isinstance(waarde, datetime):
        return waarde.strftime("%Y-%m-%d %H:%M")
    if formaat == DATUM and isinstance(waarde, date):
        return waarde.strftime("%Y-%m-%d")
    if formaat == GETAL and isinstance(waarde, float):
        return f"{waarde:g}"
    return str(waarde)


def _meta_rye(oorsig: dict) -> list[tuple[str, str]]:
    m = oorsig["meta"]
    return [
        ("Omvang", m["omvang"]),
        ("Tydperk", f"{m['van']:%Y-%m-%d} tot {m['tot']:%Y-%m-%d}"),
        ("Werksdae in tydperk", str(m["werksdae"])),
        ("Gegenereer op", m["gegenereer_op"].strftime("%Y-%m-%d %H:%M")),
        ("Gegenereer deur", f"{m['gegenereer_deur']} ({m['rol']})"),
    ]


def _verdeling(grafiek: dict) -> tuple[list[str], list[list[str]]]:
    """Enige grafiek as 'n klein tabel (vir Word, teks en skermlesers)."""
    fmt = grafiek.get("formaat", GETAL)
    if grafiek["tipe"] == "sirkel":
        totaal = sum(s["waarde"] for s in grafiek["segmente"])
        return ["", "Aantal", "Persentasie"], [
            [s["etiket"], str(s["waarde"]), f"{s['waarde'] / totaal:.0%}" if totaal else "-"]
            for s in grafiek["segmente"]
        ]
    if grafiek["tipe"] == "balk":
        return ["", "Waarde"], [[i["etiket"], formateer(i["waarde"], fmt)] for i in grafiek["items"]]
    koppe = ["Datum"] + [r["etiket"] for r in grafiek["reekse"]]
    rye = []
    for i, d in enumerate(grafiek["etikette"]):
        rye.append([formateer(d, DATUM)] + [formateer(r["waardes"][i], fmt) for r in grafiek["reekse"]])
    return koppe, rye


def _is_leeg(grafiek: dict) -> bool:
    if grafiek["tipe"] == "sirkel":
        return not any(s["waarde"] for s in grafiek["segmente"])
    if grafiek["tipe"] == "balk":
        return not grafiek["items"]
    return not grafiek["etikette"]


# --------------------------------------------------------------------------- #
# Excel
# --------------------------------------------------------------------------- #

def skryf_xlsx(oorsig: dict) -> bytes:
    from openpyxl import Workbook
    from openpyxl.chart import BarChart, LineChart, PieChart, Reference
    from openpyxl.chart.label import DataLabelList
    from openpyxl.chart.series import DataPoint
    from openpyxl.formatting.rule import CellIsRule
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    kop_vul = PatternFill("solid", fgColor=_NAVY)
    kop_font = Font(bold=True, color="FFFFFF")
    titel_font = Font(bold=True, size=16, color=_NAVY)
    sub_font = Font(bold=True, size=12, color=_NAVY)
    rooi = PatternFill("solid", fgColor="F8D7DA")
    groen = PatternFill("solid", fgColor="D4EDDA")
    dun = Side(style="thin", color="D0D7DE")
    rand = Border(left=dun, right=dun, top=dun, bottom=dun)
    xl_formaat = {PERSENT: "0%", DATUM: "yyyy-mm-dd", DATUMTYD: "yyyy-mm-dd hh:mm"}

    wb = Workbook()
    wb.remove(wb.active)

    for afdeling in oorsig["afdelings"]:
        ws = wb.create_sheet(afdeling["titel"])
        ws["A1"] = f"{oorsig['titel']} — {afdeling['titel']}"
        ws["A1"].font = titel_font
        ws["A2"] = afdeling["beskrywing"]
        ws["A2"].font = Font(italic=True, color="555555")

        ry = 4
        for k, v in _meta_rye(oorsig):
            ws.cell(row=ry, column=1, value=k).font = Font(bold=True)
            ws.cell(row=ry, column=2, value=v)
            ry += 1

        ry += 1
        ws.cell(row=ry, column=1, value="Kernsyfers").font = sub_font
        for s in afdeling["kernsyfers"]:
            ry += 1
            ws.cell(row=ry, column=1, value=s["etiket"])
            sel = ws.cell(row=ry, column=2, value=s["waarde"] if s["waarde"] is not None else "n.v.t.")
            sel.font = Font(bold=True)
            sel.alignment = Alignment(horizontal="left")
            if s["waarde"] is not None and s["formaat"] in xl_formaat:
                sel.number_format = xl_formaat[s["formaat"]]

        ry += 2
        ws.cell(row=ry, column=1, value="Wat die data wys").font = sub_font
        for insig in afdeling["insigte"]:
            ry += 1
            ws.cell(row=ry, column=1, value=f"• {insig}")

        # --- Tabelle onder mekaar ---
        breedtes: dict[int, int] = {1: 34, 2: 22}
        eerste_tabel = True
        for tabel in afdeling["tabelle"]:
            ry += 3
            ws.cell(row=ry, column=1, value=f"{tabel['titel']} ({tabel['totaal']})").font = sub_font
            ry += 1
            kop_ry = ry
            for k, kol in enumerate(tabel["kolomme"], start=1):
                sel = ws.cell(row=ry, column=k, value=kol["naam"])
                sel.fill = kop_vul
                sel.font = kop_font
                sel.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                sel.border = rand
                breedtes[k] = max(breedtes.get(k, 0), min(len(kol["naam"]) + 4, 40))
            for data_ry in tabel["rye"]:
                ry += 1
                for k, (waarde, kol) in enumerate(zip(data_ry, tabel["kolomme"]), start=1):
                    sel = ws.cell(row=ry, column=k, value=waarde)
                    sel.border = rand
                    if kol["formaat"] in xl_formaat:
                        sel.number_format = xl_formaat[kol["formaat"]]
                    lengte = 17 if kol["formaat"] == DATUMTYD else len(formateer(waarde, kol["formaat"]))
                    breedtes[k] = max(breedtes.get(k, 0), min(lengte + 2, 40))
            if not tabel["rye"]:
                ry += 1
                ws.cell(row=ry, column=1, value="Geen data nie.").font = Font(italic=True, color="888888")
            elif eerste_tabel:
                # Excel laat net een outo-filter per blad toe: die hooftabel kry dit.
                ws.auto_filter.ref = f"A{kop_ry}:{get_column_letter(len(tabel['kolomme']))}{ry}"
            if tabel["rye"]:
                for k, kol in enumerate(tabel["kolomme"], start=1):
                    if kol["formaat"] == PERSENT:
                        bereik = f"{get_column_letter(k)}{kop_ry + 1}:{get_column_letter(k)}{ry}"
                        ws.conditional_formatting.add(bereik, CellIsRule(
                            operator="lessThan", formula=[str(LAE_BYWONING)], fill=rooi))
                        ws.conditional_formatting.add(bereik, CellIsRule(
                            operator="greaterThanOrEqual", formula=["0.9"], fill=groen))
            eerste_tabel = False

        for k, w in breedtes.items():
            ws.column_dimensions[get_column_letter(k)].width = w

        # --- Grafieke regs van die tabelle; hul brondata nog verder regs ---
        maks_kol = max(breedtes)
        grafiek_kol = get_column_letter(maks_kol + 2)
        data_kol = maks_kol + 12
        data_ry = 1
        ws.cell(row=data_ry, column=data_kol, value="Grafiekdata").font = sub_font
        data_ry += 2
        grafiek_ry = 1

        for g in afdeling["grafieke"]:
            if _is_leeg(g):
                continue
            persent = g.get("formaat") == PERSENT
            if g["tipe"] == "sirkel":
                rye = [(s["etiket"], s["waarde"]) for s in g["segmente"]]
                reeks_name = ["Aantal"]
            elif g["tipe"] == "balk":
                rye = [(i["etiket"], i["waarde"]) for i in g["items"]]
                reeks_name = ["Bywoning %" if persent else "Aantal"]
            else:
                reeks_name = [r["etiket"] for r in g["reekse"]]
                rye = [(d, *[r["waardes"][i] for r in g["reekse"]]) for i, d in enumerate(g["etikette"])]

            ws.cell(row=data_ry, column=data_kol, value=g["titel"]).font = Font(bold=True)
            for j, naam in enumerate(reeks_name, start=1):
                ws.cell(row=data_ry, column=data_kol + j, value=naam).font = Font(bold=True)
            begin = data_ry
            for r in rye:
                data_ry += 1
                for j, waarde in enumerate(r):
                    sel = ws.cell(row=data_ry, column=data_kol + j, value=waarde)
                    if j == 0 and isinstance(waarde, date):
                        sel.number_format = "yyyy-mm-dd"
                    elif j > 0 and persent:
                        sel.number_format = "0%"
            kategorieë = Reference(ws, min_col=data_kol, min_row=begin + 1, max_row=data_ry)

            if g["tipe"] == "sirkel":
                grafiek = PieChart()
                grafiek.add_data(Reference(ws, min_col=data_kol + 1, min_row=begin, max_row=data_ry),
                                 titles_from_data=True)
                grafiek.set_categories(kategorieë)
                grafiek.dataLabels = DataLabelList()
                grafiek.dataLabels.showPercent = True
                for i in range(len(rye)):
                    punt = DataPoint(idx=i)
                    punt.graphicalProperties.solidFill = _KLEURE[min(i, len(_KLEURE) - 1)]
                    punt.graphicalProperties.line.solidFill = "FFFFFF"
                    grafiek.series[0].dPt.append(punt)
            elif g["tipe"] == "balk":
                grafiek = BarChart()
                grafiek.type = "bar"
                grafiek.legend = None
                grafiek.add_data(Reference(ws, min_col=data_kol + 1, min_row=begin, max_row=data_ry),
                                 titles_from_data=True)
                grafiek.set_categories(kategorieë)
                grafiek.series[0].graphicalProperties.solidFill = _KLEURE[0]
                grafiek.y_axis.scaling.min = 0
                if persent:
                    grafiek.y_axis.number_format = "0%"
                    grafiek.y_axis.scaling.max = 1
                grafiek.x_axis.scaling.orientation = "maxMin"  # eerste item bo
                grafiek.x_axis.delete = False
                grafiek.y_axis.delete = False
            else:
                grafiek = LineChart()
                grafiek.add_data(Reference(ws, min_col=data_kol + 1, max_col=data_kol + len(reeks_name),
                                           min_row=begin, max_row=data_ry), titles_from_data=True)
                grafiek.set_categories(kategorieë)
                for i, reeks in enumerate(grafiek.series):
                    reeks.graphicalProperties.line.solidFill = _KLEURE[min(i, 1)]
                    reeks.graphicalProperties.line.width = 22000
                    reeks.smooth = False
                grafiek.x_axis.number_format = "dd mmm"
                grafiek.y_axis.scaling.min = 0
                if persent:
                    grafiek.y_axis.number_format = "0%"
                    grafiek.y_axis.scaling.max = 1
                if len(reeks_name) == 1:
                    grafiek.legend = None
                grafiek.x_axis.delete = False
                grafiek.y_axis.delete = False

            grafiek.title = g["titel"]
            grafiek.height, grafiek.width = 7.5, 15
            ws.add_chart(grafiek, f"{grafiek_kol}{grafiek_ry}")
            grafiek_ry += 17
            data_ry += 2

        ws.column_dimensions[get_column_letter(data_kol)].width = 26

    if not wb.sheetnames:
        wb.create_sheet("Verslag")
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


# --------------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------------- #

def skryf_pdf(oorsig: dict) -> bytes:
    from reportlab.graphics.charts.barcharts import HorizontalBarChart
    from reportlab.graphics.charts.legends import Legend
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.shapes import Drawing, String
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    kleure = [colors.HexColor("#" + k) for k in _KLEURE]
    navy = colors.HexColor("#" + _NAVY)
    style = getSampleStyleSheet()
    titel_s = ParagraphStyle("titel", parent=style["Title"], textColor=navy, alignment=0, fontSize=20)
    h1 = ParagraphStyle("h1", parent=style["Heading1"], textColor=navy, fontSize=16)
    h2 = ParagraphStyle("h2", parent=style["Heading2"], textColor=navy, fontSize=12, spaceBefore=10)
    gewoon = ParagraphStyle("gewoon", parent=style["BodyText"], fontSize=9, leading=12)
    sel_s = ParagraphStyle("sel", parent=style["BodyText"], fontSize=7, leading=8.5)
    kop_s = ParagraphStyle("kop", parent=sel_s, textColor=colors.white, fontName="Helvetica-Bold")
    nota_s = ParagraphStyle("nota", parent=gewoon, textColor=colors.HexColor("#777777"), fontSize=8)

    bladsy = landscape(A4)
    kantlyn = 1.5 * cm
    breedte = bladsy[0] - 2 * kantlyn

    def p(teks, s=gewoon):
        return Paragraph(escape(str(teks)), s)

    def grafiek_tekening(g: dict, w: float = 360, h: float = 200) -> Drawing:
        d = Drawing(w, h)
        d.add(String(0, h - 12, g["titel"], fontName="Helvetica-Bold", fontSize=9, fillColor=navy))
        if _is_leeg(g):
            d.add(String(w / 2, h / 2, "Geen data nie", textAnchor="middle", fontSize=9,
                         fillColor=colors.grey))
            return d
        persent = g.get("formaat") == PERSENT

        if g["tipe"] == "sirkel":
            segmente = g["segmente"]
            totaal = sum(s["waarde"] for s in segmente)
            nie_nul = [(i, s) for i, s in enumerate(segmente) if s["waarde"] > 0]
            pie = Pie()
            pie.x, pie.y = 10, 20
            pie.width = pie.height = min(h - 45, 150)
            pie.data = [s["waarde"] for _, s in nie_nul]
            pie.innerRadiusFraction = 0.55
            pie.slices.strokeColor = colors.white
            pie.slices.strokeWidth = 2
            for j, (i, _) in enumerate(nie_nul):
                pie.slices[j].fillColor = kleure[min(i, len(kleure) - 1)]
            d.add(pie)
            d.add(String(pie.x + pie.width / 2, pie.y + pie.height / 2 - 5, str(totaal),
                         textAnchor="middle", fontName="Helvetica-Bold", fontSize=14))
            lg = Legend()
            lg.x, lg.y = pie.x + pie.width + 25, pie.y + pie.height - 10
            lg.boxAnchor = "nw"
            lg.fontName, lg.fontSize = "Helvetica", 8
            lg.dx = lg.dy = 8
            lg.deltay = 14
            lg.alignment = "right"
            lg.colorNamePairs = [
                (kleure[min(i, len(kleure) - 1)], f"{s['etiket']}: {s['waarde']} ({s['waarde'] / totaal:.0%})")
                for i, s in enumerate(segmente)
            ]
            d.add(lg)
            return d

        if g["tipe"] == "balk":
            items = list(reversed(g["items"]))  # reportlab teken van onder na bo
            waardes = [i["waarde"] * 100 if persent else i["waarde"] for i in items]
            bc = HorizontalBarChart()
            bc.x, bc.y = 120, 15
            bc.width, bc.height = w - 150, h - 40
            bc.data = [tuple(waardes)]
            bc.categoryAxis.categoryNames = [i["etiket"][:22] for i in items]
            bc.categoryAxis.labels.fontSize = 7
            bc.categoryAxis.labels.boxAnchor = "e"
            bc.categoryAxis.labels.dx = -4
            bc.valueAxis.valueMin = 0
            bc.valueAxis.valueMax = 100 if persent else max(max(waardes), 1)
            bc.valueAxis.labels.fontSize = 7
            if persent:
                bc.valueAxis.labelTextFormat = "%d%%"
            bc.bars[0].fillColor = kleure[0]
            bc.bars.strokeColor = None
            bc.barLabelFormat = "%d%%" if persent else "%d"
            bc.barLabels.fontSize = 6
            bc.barLabels.boxAnchor = "w"
            bc.barLabels.dx = 3
            d.add(bc)
            return d

        etikette = g["etikette"]
        stap = max(1, len(etikette) // 10)
        lc = HorizontalLineChart()
        lc.x, lc.y = 35, 30
        lc.width, lc.height = w - 50, h - 65
        lc.data = [tuple(v * 100 if persent else v for v in r["waardes"]) for r in g["reekse"]]
        lc.categoryAxis.categoryNames = [
            d_.strftime("%d %b") if i % stap == 0 else "" for i, d_ in enumerate(etikette)
        ]
        lc.categoryAxis.labels.fontSize = 6
        lc.categoryAxis.labels.angle = 30
        lc.categoryAxis.labels.boxAnchor = "ne"
        lc.valueAxis.valueMin = 0
        hoogste = max((max(r) for r in lc.data if r), default=0)
        lc.valueAxis.valueMax = 100 if persent else max(hoogste, 1)
        lc.valueAxis.labels.fontSize = 7
        if persent:
            lc.valueAxis.labelTextFormat = "%d%%"
        for i in range(len(g["reekse"])):
            lc.lines[i].strokeColor = kleure[min(i, 1)]
            lc.lines[i].strokeWidth = 1.5
        d.add(lc)
        if len(g["reekse"]) > 1:
            lg = Legend()
            lg.x, lg.y = w - 120, h - 8
            lg.boxAnchor = "nw"
            lg.fontName, lg.fontSize = "Helvetica", 7
            lg.columnMaximum = 1
            lg.dx, lg.dy = 10, 3
            lg.deltax = 60
            lg.alignment = "right"
            lg.colorNamePairs = [(kleure[min(i, 1)], r["etiket"]) for i, r in enumerate(g["reekse"])]
            d.add(lg)
        return d

    def tabel_flowable(kolomme: list[dict], rye: list[list]):
        # Kolombreedtes volgens die inhoud, binne die bladsy se breedte.
        lengtes = []
        for k, kol in enumerate(kolomme):
            langste = max([len(kol["naam"])] + [len(formateer(r[k], kol["formaat"])) for r in rye[:300]])
            lengtes.append(min(max(langste, 6), 34))
        som = sum(lengtes)
        breedtes = [breedte * l / som for l in lengtes]
        data = [[Paragraph(escape(k["naam"]), kop_s) for k in kolomme]]
        for r in rye:
            data.append([Paragraph(escape(formateer(v, k["formaat"])), sel_s) for v, k in zip(r, kolomme)])
        t = Table(data, colWidths=breedtes, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), navy),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F4FB")]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D0D7DE")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        return t

    storie = [p(oorsig["titel"], titel_s)]
    meta = Table([[p(k + ":", ParagraphStyle("mk", parent=gewoon, fontName="Helvetica-Bold")), p(v)]
                  for k, v in _meta_rye(oorsig)], colWidths=[5 * cm, breedte - 5 * cm])
    meta.setStyle(TableStyle([("BOTTOMPADDING", (0, 0), (-1, -1), 1), ("TOPPADDING", (0, 0), (-1, -1), 1)]))
    storie += [meta, Spacer(1, 8)]
    storie.append(p("Afdelings: " + ", ".join(a["titel"] for a in oorsig["afdelings"]), nota_s))

    for afdeling in oorsig["afdelings"]:
        storie += [PageBreak(), p(afdeling["titel"], h1), p(afdeling["beskrywing"], nota_s), Spacer(1, 6)]

        # Kernsyfers as teëls: vier per ry.
        waarde_s = ParagraphStyle("sw", parent=gewoon, fontName="Helvetica-Bold", fontSize=14, leading=17)
        syfers = [[[p(s["etiket"], nota_s)], [p(formateer(s["waarde"], s["formaat"], "n.v.t."), waarde_s)]]
                  for s in afdeling["kernsyfers"]]
        selle = [Table(s, colWidths=[breedte / 4 - 14]) for s in syfers]
        rooster = [selle[i:i + 4] + [""] * (4 - len(selle[i:i + 4])) for i in range(0, len(selle), 4)]
        kern = Table(rooster, colWidths=[breedte / 4] * 4)
        kern.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.25, colors.HexColor("#D0D7DE")),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D0D7DE")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        storie += [kern, Spacer(1, 6)]

        if afdeling["insigte"]:
            storie.append(p("Wat die data wys", h2))
            storie += [p("• " + i) for i in afdeling["insigte"]]

        if afdeling["grafieke"]:
            storie.append(p("Grafieke", h2))
            tekeninge = [grafiek_tekening(g) for g in afdeling["grafieke"]]
            rye = [tekeninge[i:i + 2] + [""] * (2 - len(tekeninge[i:i + 2])) for i in range(0, len(tekeninge), 2)]
            storie.append(Table(rye, colWidths=[breedte / 2] * 2))

        for tabel in afdeling["tabelle"]:
            storie.append(p(f"{tabel['titel']} ({tabel['totaal']})", h2))
            if not tabel["rye"]:
                storie.append(p("Geen data nie.", nota_s))
                continue
            rye = tabel["rye"][:MAKS_DOKUMENT_RYE]
            storie.append(tabel_flowable(tabel["kolomme"], rye))
            if len(tabel["rye"]) > len(rye):
                storie.append(p(f"Net die eerste {len(rye)} van {len(tabel['rye'])} rye word gewys. "
                                f"Laai die Excel-verslag af vir alles.", nota_s))

    def voetskrif(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.grey)
        canvas.drawString(kantlyn, 0.8 * cm, f"{oorsig['titel']} · {oorsig['meta']['omvang']}")
        canvas.drawRightString(bladsy[0] - kantlyn, 0.8 * cm, f"Bladsy {doc.page}")
        canvas.restoreState()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=bladsy, leftMargin=kantlyn, rightMargin=kantlyn,
                            topMargin=kantlyn, bottomMargin=kantlyn, title=oorsig["titel"],
                            author=oorsig["meta"]["gegenereer_deur"])
    doc.build(storie, onFirstPage=voetskrif, onLaterPages=voetskrif)
    return buffer.getvalue()


# --------------------------------------------------------------------------- #
# Word
# --------------------------------------------------------------------------- #

def skryf_docx(oorsig: dict) -> bytes:
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.shared import Cm, Pt, RGBColor

    doc = Document()
    seksie = doc.sections[0]
    seksie.orientation = WD_ORIENT.LANDSCAPE
    seksie.page_width, seksie.page_height = seksie.page_height, seksie.page_width
    for kant in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(seksie, kant, Cm(1.5))
    doc.styles["Normal"].font.size = Pt(9)

    def tabel(koppe: list[str], rye: list[list[str]], styl: str = "Light Grid Accent 1"):
        t = doc.add_table(rows=len(rye) + 1, cols=len(koppe))
        t.style = styl
        for k, kop in enumerate(koppe):
            sel = t.rows[0].cells[k]
            sel.text = kop
            for run in sel.paragraphs[0].runs:
                run.font.bold = True
        for i, ry in enumerate(rye, start=1):
            selle = t.rows[i].cells
            for k, waarde in enumerate(ry):
                selle[k].text = waarde
        return t

    def nota(teks: str):
        run = doc.add_paragraph().add_run(teks)
        run.italic = True
        run.font.color.rgb = RGBColor(0x77, 0x77, 0x77)

    doc.add_heading(oorsig["titel"], 0)
    for k, v in _meta_rye(oorsig):
        para = doc.add_paragraph()
        para.add_run(f"{k}: ").bold = True
        para.add_run(v)

    for afdeling in oorsig["afdelings"]:
        doc.add_page_break()
        doc.add_heading(afdeling["titel"], 1)
        nota(afdeling["beskrywing"])

        doc.add_heading("Kernsyfers", 2)
        tabel(["Syfer", "Waarde"],
              [[s["etiket"], formateer(s["waarde"], s["formaat"], "n.v.t.")] for s in afdeling["kernsyfers"]],
              "Light List Accent 1")

        if afdeling["insigte"]:
            doc.add_heading("Wat die data wys", 2)
            for insig in afdeling["insigte"]:
                doc.add_paragraph(insig, style="List Bullet")

        if afdeling["grafieke"]:
            doc.add_heading("Verdelings", 2)
            for g in afdeling["grafieke"]:
                doc.add_heading(g["titel"], 3)
                if _is_leeg(g):
                    nota("Geen data nie.")
                    continue
                koppe, rye = _verdeling(g)
                tabel(koppe, rye, "Light List Accent 1")

        for t in afdeling["tabelle"]:
            doc.add_heading(f"{t['titel']} ({t['totaal']})", 2)
            if not t["rye"]:
                nota("Geen data nie.")
                continue
            rye = t["rye"][:MAKS_DOKUMENT_RYE]
            tabel([k["naam"] for k in t["kolomme"]],
                  [[formateer(v, k["formaat"]) for v, k in zip(r, t["kolomme"])] for r in rye])
            if len(t["rye"]) > len(rye):
                nota(f"Net die eerste {len(rye)} van {len(t['rye'])} rye word gewys. "
                     f"Laai die Excel-verslag af vir alles.")

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


# --------------------------------------------------------------------------- #
# Teks
# --------------------------------------------------------------------------- #

def _teks_tabel(koppe: list[str], rye: list[list[str]], maks_breedte: int = 32) -> list[str]:
    def kort(s: str) -> str:
        return s if len(s) <= maks_breedte else s[: maks_breedte - 1] + "…"

    rye = [[kort(s) for s in r] for r in rye]
    koppe = [kort(k) for k in koppe]
    breedtes = [max([len(k)] + [len(r[i]) for r in rye]) for i, k in enumerate(koppe)]
    lyne = [
        "  " + " | ".join(k.ljust(b) for k, b in zip(koppe, breedtes)),
        "  " + "-+-".join("-" * b for b in breedtes),
    ]
    lyne += ["  " + " | ".join(s.ljust(b) for s, b in zip(r, breedtes)) for r in rye]
    return lyne


def skryf_txt(oorsig: dict) -> bytes:
    lyne = [oorsig["titel"], "=" * len(oorsig["titel"]), ""]
    meta = _meta_rye(oorsig)
    wydte = max(len(k) for k, _ in meta)
    lyne += [f"{k.ljust(wydte)} : {v}" for k, v in meta]

    for afdeling in oorsig["afdelings"]:
        kop = f" {afdeling['titel'].upper()} "
        lyne += ["", "", kop.center(78, "="), afdeling["beskrywing"], ""]

        lyne.append("Kernsyfers")
        wydte = max(len(s["etiket"]) for s in afdeling["kernsyfers"])
        lyne += [f"  {s['etiket'].ljust(wydte, '.')} {formateer(s['waarde'], s['formaat'], 'n.v.t.')}"
                 for s in afdeling["kernsyfers"]]

        if afdeling["insigte"]:
            lyne += ["", "Wat die data wys"]
            lyne += [f"  - {i}" for i in afdeling["insigte"]]

        for g in afdeling["grafieke"]:
            lyne += ["", f"Verdeling: {g['titel']}"]
            if _is_leeg(g):
                lyne.append("  Geen data nie.")
                continue
            koppe, rye = _verdeling(g)
            lyne += _teks_tabel(koppe, rye)

        for t in afdeling["tabelle"]:
            lyne += ["", f"{t['titel']} ({t['totaal']})"]
            if not t["rye"]:
                lyne.append("  Geen data nie.")
                continue
            lyne += _teks_tabel(
                [k["naam"] for k in t["kolomme"]],
                [[formateer(v, k["formaat"]) for v, k in zip(r, t["kolomme"])] for r in t["rye"]],
            )

    return ("\n".join(lyne) + "\n").encode("utf-8")


SKRYWERS: dict[str, Callable[[dict], bytes]] = {
    "xlsx": skryf_xlsx,
    "pdf": skryf_pdf,
    "docx": skryf_docx,
    "txt": skryf_txt,
}


def skryf_verslag(oorsig: dict, formaat: str) -> bytes:
    skrywer: Optional[Callable[[dict], bytes]] = SKRYWERS.get(formaat)
    if skrywer is None:
        raise HTTPException(status_code=400, detail=f"Onbekende formaat '{formaat}'; gebruik xlsx, pdf, docx of txt")
    return skrywer(oorsig)
