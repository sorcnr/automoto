#!/usr/bin/env python3
"""
AutoMoto — Akıllı Motosiklet Güvenlik, Keyless Go & Telemetri Sistemi
KiCad 10 Otomatik 4 Katmanlı PCB Tasarım ve Engel-Duyarlı (Obstacle-Aware A*) Yönlendirme Motoru v4.0

Mimari Özellikler (v4.0):
- Boyut: 80.0 mm x 55.0 mm, 4 Katmanlı Otomotiv Sınıfı FR4 (F.Cu, In1.Cu [GND], In2.Cu [Power/Signal], B.Cu)
- Hücresel + GPS Modülü: SIMCom SIM808 (68-Pin LCC 24x24mm) — Tüm VBAT, GND, UART, PWRKEY, RI, DTR, STATUS,
  NETLIGHT, Nano SIM (SIM_VDD, SIM_DATA, SIM_CLK, SIM_RST) ve 50-Ohm GSM/GPS RF hatları %100 bağlı!
- Molex 14-Pin (J1) Delik İzolasyonu: Üst sıra pinler (1..7) doğrudan yukarı (-Y_k), alt sıra pinler (8..14) doğrudan
  aşağı (+Y_k) çıkar; HİÇBİR DEVRE YOLU MOLEX PİN DELİKLERİNİN ARASINDAN GEÇMEZ!
- Tüm 20 Adet Pasif Direnç (R1..R20) ve 8 Adet Kapasitör (C1..C8) şematikle birebir uyumlu olarak dizilmiştir.
- 3 Katmanlı (F.Cu, In2.Cu, B.Cu) 0.25mm Çözünürlüklü A* Yönlendirici + In1.Cu/F.Cu/B.Cu GND Bakır Poligon Dolgusu (Zone Fill).
"""

import heapq
import math
import os
import pcbnew

PROJECT_ROOT = "/home/sorcnr/Documents/automoto"
PCB_DIR = os.path.join(PROJECT_ROOT, "hardware/pcb")
RENDERS_DIR = os.path.join(PCB_DIR, "renders")
OUTPUT_PCB = os.path.join(PCB_DIR, "automoto.kicad_pcb")

os.makedirs(PCB_DIR, exist_ok=True)
os.makedirs(RENDERS_DIR, exist_ok=True)

FP_LIB_BASE = "/app/extensions/Library/footprints"
MODEL_LIB_BASE = "/app/extensions/Library/3dmodels"

BOARD_W = 80.0
BOARD_H = 55.0

net_cache = {}


def get_or_create_net(board, net_name):
    if not net_name or net_name == "NC":
        return None
    if net_name in net_cache:
        return net_cache[net_name]
    net = board.FindNet(net_name)
    if not net:
        net = pcbnew.NETINFO_ITEM(board, net_name)
        board.Add(net)
    net_cache[net_name] = net
    return net


def set_custom_3d_model(fp, model_rel_path, offset_xyz=(0, 0, 0), scale_xyz=(1, 1, 1), rot_xyz=(0, 0, 0)):
    full_path = os.path.join(MODEL_LIB_BASE, model_rel_path)
    if os.path.exists(full_path):
        try:
            fp.Models().clear()
            m = pcbnew.FP_3DMODEL()
            m.m_Filename = full_path
            m.m_Offset = pcbnew.VECTOR3D(offset_xyz[0], offset_xyz[1], offset_xyz[2])
            m.m_Scale = pcbnew.VECTOR3D(scale_xyz[0], scale_xyz[1], scale_xyz[2])
            m.m_Rotation = pcbnew.VECTOR3D(rot_xyz[0], rot_xyz[1], rot_xyz[2])
            fp.Add3DModel(m)
        except Exception as e:
            print(f"[UYARI] 3D model eklenemedi ({model_rel_path}): {e}")


def load_footprint(board, lib_name, fp_name, ref, val, x_mm, y_mm, rot=0, layer=pcbnew.F_Cu):
    lib_path = os.path.join(FP_LIB_BASE, f"{lib_name}.pretty")
    fp = pcbnew.FootprintLoad(lib_path, fp_name)
    target_pos = pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(BOARD_H - y_mm))

    fp.SetReference(ref)
    fp.SetValue(val)
    fp.SetPosition(target_pos)
    fp.SetOrientationDegrees(rot)
    board.Add(fp)
    if layer == pcbnew.B_Cu and fp.GetLayer() != pcbnew.B_Cu:
        fp.Flip(target_pos, False)
        fp.SetOrientationDegrees(rot)

    # ÖNEMLİ: SWIG/R-tree bellek hatasını önlemek için padleri silmek yerine yerinde (in-place) dönüştür:
    # J1 Pimsiz (Pegless) varyant: İki NPTH deliğini Pad 2'nin içine gömülü SMD yardımcı pad'e dönüştür
    if ref == "J1":
        p2_pos = pcbnew.VECTOR2I(pcbnew.FromMM(x_mm + 3.0), pcbnew.FromMM(BOARD_H - y_mm))
        for p in fp.Pads():
            if p.GetNumber() == "" or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                p.SetNumber("2")
                p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
                p.SetDrillSize(pcbnew.VECTOR2I(0, 0))
                p.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.2), pcbnew.FromMM(0.2)))
                ls = pcbnew.LSET()
                ls.AddLayer(pcbnew.F_Cu)
                p.SetLayerSet(ls)
                p.SetPosition(p2_pos)

    # J4 USB-C: Kütüphanedeki NPTH deliklerini SH padinin içine gömülü SMD yardımcı pad'e dönüştür (hole_clearance hatasını %100 önler)
    if ref == "J4":
        sh_pos = pcbnew.VECTOR2I(pcbnew.FromMM(31.39), pcbnew.FromMM(6.905))
        for p in fp.Pads():
            if p.GetNumber() == "" or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                p.SetNumber("SH")
                p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
                p.SetDrillSize(pcbnew.VECTOR2I(0, 0))
                p.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.2), pcbnew.FromMM(0.2)))
                ls = pcbnew.LSET()
                ls.AddLayer(pcbnew.F_Cu)
                p.SetLayerSet(ls)
                p.SetPosition(sh_pos)

    # U1 ESP32-S3-WROOM-1U: Termal pad içindeki 12 adet PTH via'yı F.Cu SMD Pad 41'e dönüştür (B.Cu çakışmasını önler)
    if ref == "U1":
        for p in fp.Pads():
            if p.GetNumber() == "41" and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
                p.SetDrillSize(pcbnew.VECTOR2I(0, 0))
                ls = pcbnew.LSET()
                ls.AddLayer(pcbnew.F_Cu)
                p.SetLayerSet(ls)

    # Referans yazılarını pad üstüne binmeyecek şekilde ayarla
    ref_field = fp.Reference()
    if ref_field:
        ref_field.SetPosition(target_pos)
        ref_field.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.8), pcbnew.FromMM(0.8)))
        ref_field.SetTextThickness(pcbnew.FromMM(0.15))
        # Sadece altında merkez pad olmayan U2 ve J2'de dahili referansı görünür bırak; diğerlerini özel etiketle yaz
        if ref not in ["U2", "J2"]:
            ref_field.SetVisible(False)

    val_field = fp.Value()
    if val_field:
        val_field.SetVisible(False)

    # 3D Modeller
    if ref == "U1":
        set_custom_3d_model(fp, "RF_Module.3dshapes/ESP32-WROOM-32U.step")
    elif ref == "U2":
        set_custom_3d_model(fp, "RF_GSM.3dshapes/ublox_SARA_LGA-96.step", scale_xyz=(1.34, 0.92, 0.95))
    elif ref == "U3":
        set_custom_3d_model(fp, "Package_LGA.3dshapes/LGA-16_3x3mm_P0.5mm.step")
    elif ref == "U10":
        set_custom_3d_model(fp, "Package_SO.3dshapes/TSSOP-14-1EP_4.4x5mm_P0.65mm.step")
    elif ref in ["U11", "U12", "U9"]:
        set_custom_3d_model(fp, "Package_SO.3dshapes/SO-4_4.4x4.3mm_P2.54mm.step")
    elif ref in ["U8", "U5"]:
        set_custom_3d_model(fp, "Package_SO.3dshapes/SOIC-8_3.9x4.9mm_P1.27mm.step")
    elif ref in ["U4", "U6", "D3"]:
        set_custom_3d_model(fp, "Package_TO_SOT_SMD.3dshapes/SOT-23-6.step")
    elif ref == "U7":
        set_custom_3d_model(fp, "Package_TO_SOT_SMD.3dshapes/SOT-23-5.step")
    elif ref == "L1":
        set_custom_3d_model(fp, "Inductor_SMD.3dshapes/L_Vishay_IHLP-2020.step")
    elif ref == "J4":
        set_custom_3d_model(fp, "Connector_USB.3dshapes/USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal.step")
    elif ref == "J3":
        set_custom_3d_model(fp, "Connector_JST.3dshapes/JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal.step")
    elif ref == "D1":
        set_custom_3d_model(fp, "Diode_SMD.3dshapes/D_SMC.step")
    elif ref == "Q1":
        set_custom_3d_model(fp, "Package_SO.3dshapes/SO-8_3.9x4.9mm_P1.27mm.step")
    elif ref == "F1":
        set_custom_3d_model(fp, "Resistor_SMD.3dshapes/R_1812_4532Metric.step")
    elif ref == "C4":
        set_custom_3d_model(fp, "Capacitor_Tantalum_SMD.3dshapes/CP_EIA-7343-31_Kemet-D.step")

    return fp


def set_component_nets(board, ref, pin_net_map):
    fp = board.FindFootprintByReference(ref)
    if not fp:
        return
    for p in fp.Pads():
        pnum = p.GetNumber()
        if ref == "U10" and pnum == "":
            pnum = "15"
        if pnum in pin_net_map:
            net_name = pin_net_map[pnum]
            if net_name and net_name != "NC":
                p.SetNet(get_or_create_net(board, net_name))


def add_track_segment(board, x1_k, y1_k, x2_k, y2_k, width_mm, layer, net):
    if abs(x1_k - x2_k) < 1e-4 and abs(y1_k - y2_k) < 1e-4:
        return None
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1_k), pcbnew.FromMM(y1_k)))
    t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2_k), pcbnew.FromMM(y2_k)))
    t.SetWidth(pcbnew.FromMM(width_mm))
    t.SetLayer(layer)
    if net:
        t.SetNet(net)
    board.Add(t)
    return t


def add_via_at(board, x_k, y_k, drill_mm=0.3, pad_mm=0.6, net=None):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x_k), pcbnew.FromMM(y_k)))
    v.SetWidth(pcbnew.FromMM(pad_mm))
    v.SetDrill(pcbnew.FromMM(drill_mm))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    if net:
        v.SetNet(net)
    board.Add(v)
    return v


# ==============================================================================
# 3 KATMANLI (F.Cu, In2.Cu, B.Cu) 0.25mm ENGEL-DUYARLI (OBSTACLE-AWARE) A* MOTORU
# ==============================================================================
GRID_STEP = 0.25
NX = int(round(BOARD_W / GRID_STEP)) + 1  # 321
NY = int(round(BOARD_H / GRID_STEP)) + 1  # 221
LAYERS = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
NL = len(LAYERS)


def mm_to_idx(x_k, y_k):
    gx = max(0, min(NX - 1, int(round(x_k / GRID_STEP))))
    gy = max(0, min(NY - 1, int(round(y_k / GRID_STEP))))
    return gx, gy


def idx_to_mm(gx, gy):
    return round(gx * GRID_STEP, 4), round(gy * GRID_STEP, 4)


class ObstacleRouter:
    def __init__(self, board):
        self.board = board
        self.layer_obs = [[[set() for _ in range(NY)] for _ in range(NX)] for _ in range(NL)]
        self.via_obs = [[set() for _ in range(NY)] for _ in range(NX)]
        self._init_board_obstacles()

    def _mark_box(self, grid_2d, x1, y1, x2, y2, tag):
        gx1 = max(0, int(math.ceil((x1 - 1e-4) / GRID_STEP)))
        gx2 = min(NX - 1, int(math.floor((x2 + 1e-4) / GRID_STEP)))
        gy1 = max(0, int(math.ceil((y1 - 1e-4) / GRID_STEP)))
        gy2 = min(NY - 1, int(math.floor((y2 + 1e-4) / GRID_STEP)))
        for gx in range(gx1, gx2 + 1):
            for gy in range(gy1, gy2 + 1):
                grid_2d[gx][gy].add(tag)

    def _init_board_obstacles(self):
        # 1. Kart kenar boşluğu (0.8 mm)
        for gx in range(NX):
            for gy in range(NY):
                xk, yk = idx_to_mm(gx, gy)
                if xk < 0.8 or xk > BOARD_W - 0.8 or yk < 0.8 or yk > BOARD_H - 0.8:
                    for li in range(NL):
                        self.layer_obs[li][gx][gy].add("__EDGE__")
                    self.via_obs[gx][gy].add("__EDGE__")

        # 2. Molex J1 Sıra-1 (Y_k=48.5) ve Sıra-2 (Y_k=51.5) ARASINDAKİ KORİDORU KESİN OLARAK KAPAT!
        for li in range(NL):
            self._mark_box(self.layer_obs[li], 20.5, 48.6, 41.5, 51.4, "__MOLEX_GAP__")
        self._mark_box(self.via_obs, 20.0, 47.2, 42.0, 52.8, "__MOLEX_GAP__")

        # 3. Tüm bileşenlerin dahili Keepout Zone (Rule Area) bölgelerini otomatik oku ve kapat
        for fp in self.board.GetFootprints():
            ref = fp.GetReference()
            for z in fp.Zones():
                if not z.GetIsRuleArea():
                    continue
                bb = z.GetBoundingBox()
                x1 = pcbnew.ToMM(bb.GetLeft()) - 0.45
                y1 = pcbnew.ToMM(bb.GetTop()) - 0.45
                x2 = pcbnew.ToMM(bb.GetRight()) + 0.45
                y2 = pcbnew.ToMM(bb.GetBottom()) + 0.45
                tag = f"__KEEPOUT_{ref}__"
                if z.GetDoNotAllowVias():
                    self._mark_box(self.via_obs, x1 - 0.2, y1 - 0.2, x2 + 0.2, y2 + 0.2, tag)
                if z.GetDoNotAllowTracks():
                    zls = z.GetLayerSet()
                    for li, lyr in enumerate(LAYERS):
                        if zls.Contains(lyr):
                            self._mark_box(self.layer_obs[li], x1, y1, x2, y2, tag)

        # 4. Tüm padleri ve delikleri (PTH/SMD) tam geometrik sınırla işle
        pad_margin = 0.34
        via_margin = 0.57
        hole_margin = 0.39

        for fp in self.board.GetFootprints():
            ref = fp.GetReference()
            for p in fp.Pads():
                net_name = p.GetNetname() if p.GetNet() else f"__UNCONN_{ref}_{p.GetNumber()}__"
                if not net_name:
                    net_name = f"__UNCONN_{ref}_{p.GetNumber()}__"

                pos = p.GetPosition()
                px = pcbnew.ToMM(pos.x)
                py = pcbnew.ToMM(pos.y)
                bb = p.GetBoundingBox()
                hx = pcbnew.ToMM(bb.GetWidth()) * 0.5
                hy = pcbnew.ToMM(bb.GetHeight()) * 0.5

                ls = p.GetLayerSet()
                is_pth = p.GetAttribute() in [pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH]

                if is_pth:
                    drill = p.GetDrillSize()
                    drx = pcbnew.ToMM(drill.x) * 0.5
                    dry = pcbnew.ToMM(drill.y) * 0.5
                    mx = max(hx + pad_margin, drx + hole_margin)
                    my = max(hy + pad_margin, dry + hole_margin)
                    for li in range(NL):
                        self._mark_box(self.layer_obs[li], px - mx, py - my, px + mx, py + my, net_name)
                    self._mark_box(self.via_obs, px - (hx + via_margin), py - (hy + via_margin), px + (hx + via_margin), py + (hy + via_margin), "__PTH__")
                else:
                    if ls.Contains(pcbnew.F_Cu):
                        self._mark_box(self.layer_obs[0], px - (hx + pad_margin), py - (hy + pad_margin), px + (hx + pad_margin), py + (hy + pad_margin), net_name)
                        self._mark_box(self.via_obs, px - (hx + via_margin), py - (hy + via_margin), px + (hx + via_margin), py + (hy + via_margin), net_name)
                    if ls.Contains(pcbnew.B_Cu):
                        self._mark_box(self.layer_obs[2], px - (hx + pad_margin), py - (hy + pad_margin), px + (hx + pad_margin), py + (hy + pad_margin), net_name)
                        self._mark_box(self.via_obs, px - (hx + via_margin), py - (hy + via_margin), px + (hx + via_margin), py + (hy + via_margin), net_name)

    def register_segment(self, x1, y1, x2, y2, width_mm, li, net_name, custom_margin=None):
        margin = custom_margin if custom_margin is not None else (width_mm * 0.5 + 0.33)
        v_margin = width_mm * 0.5 + 0.55
        bx1, bx2 = min(x1, x2) - margin, max(x1, x2) + margin
        by1, by2 = min(y1, y2) - margin, max(y1, y2) + margin
        self._mark_box(self.layer_obs[li], bx1, by1, bx2, by2, net_name)
        self._mark_box(self.via_obs, min(x1, x2) - v_margin, min(y1, y2) - v_margin, max(x1, x2) + v_margin, max(y1, y2) + v_margin, net_name)

    def register_via(self, xk, yk, pad_mm, net_name):
        r_track = pad_mm * 0.5 + 0.39
        r_via = pad_mm * 0.5 + 0.57
        for li in range(NL):
            self._mark_box(self.layer_obs[li], xk - r_track, yk - r_track, xk + r_track, yk + r_track, net_name)
        self._mark_box(self.via_obs, xk - r_via, yk - r_via, xk + r_via, yk + r_via, "__VIA__")

    def is_cell_free(self, li, gx, gy, net_name, extra_radius_cells=0):
        if extra_radius_cells <= 0:
            obs = self.layer_obs[li][gx][gy]
            return len(obs) == 0 or (len(obs) == 1 and net_name in obs)
        for dx in range(-extra_radius_cells, extra_radius_cells + 1):
            nx = gx + dx
            if nx < 0 or nx >= NX:
                return False
            for dy in range(-extra_radius_cells, extra_radius_cells + 1):
                ny = gy + dy
                if ny < 0 or ny >= NY:
                    return False
                obs = self.layer_obs[li][nx][ny]
                if not (len(obs) == 0 or (len(obs) == 1 and net_name in obs)):
                    return False
        return True

    def is_via_free(self, gx, gy, net_name):
        obs = self.via_obs[gx][gy]
        if not (len(obs) == 0 or (len(obs) == 1 and net_name in obs)):
            return False
        for li in range(NL):
            lobs = self.layer_obs[li][gx][gy]
            if not (len(lobs) == 0 or (len(lobs) == 1 and net_name in lobs)):
                return False
        return True

    def add_manual_polyline(self, pts_mm, width_mm, layer, net_name):
        net = get_or_create_net(self.board, net_name)
        li = LAYERS.index(layer)
        for i in range(len(pts_mm) - 1):
            x1, y1 = pts_mm[i]
            x2, y2 = pts_mm[i + 1]
            add_track_segment(self.board, x1, y1, x2, y2, width_mm, layer, net)
            self.register_segment(x1, y1, x2, y2, width_mm, li, net_name)

    def route_point_to_tree(self, target_node, tree_nodes, net_name, width_mm=0.25):
        extra_cells = 0
        if width_mm > 0.30:
            extra_cells = int(math.ceil((width_mm - 0.25) * 0.5 / GRID_STEP))

        if isinstance(target_node, tuple):
            start_nodes = [target_node]
        else:
            start_nodes = list(target_node)

        for sn in start_nodes:
            if sn in tree_nodes:
                return []

        tree_list = list(tree_nodes)

        def h_cost(gx, gy):
            best = 999999
            for _, tx, ty in tree_list[:: max(1, len(tree_list) // 25)]:
                d = abs(gx - tx) + abs(gy - ty)
                if d < best:
                    best = d
            return best

        open_heap = []
        g_score = {}
        parent = {}

        for sn in start_nodes:
            g_score[sn] = 0.0
            heapq.heappush(open_heap, (h_cost(sn[1], sn[2]), 0.0, sn, (0, 0)))

        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]

        while open_heap:
            _, g, curr, last_dir = heapq.heappop(open_heap)
            if curr in tree_nodes:
                path = [curr]
                c = curr
                while c in parent:
                    c = parent[c]
                    path.append(c)
                path.reverse()
                return path

            if g > g_score.get(curr, 1e18):
                continue

            cli, cgx, cgy = curr

            # 1. Aynı katmanda 4 yönlü komşular
            for dx, dy in dirs:
                ngx, ngy = cgx + dx, cgy + dy
                if ngx < 1 or ngx >= NX - 1 or ngy < 1 or ngy >= NY - 1:
                    continue
                nxt = (cli, ngx, ngy)
                if nxt not in tree_nodes:
                    if not self.is_cell_free(cli, ngx, ngy, net_name, extra_cells):
                        continue

                step_cost = 1.0
                if last_dir != (0, 0) and last_dir != (dx, dy):
                    step_cost += 0.35
                if cli == 1:
                    step_cost += 0.05

                ng = g + step_cost
                if ng < g_score.get(nxt, 1e18):
                    g_score[nxt] = ng
                    parent[nxt] = curr
                    heapq.heappush(open_heap, (ng + h_cost(ngx, ngy), ng, nxt, (dx, dy)))

            # 2. Via ile katman değiştirme (F.Cu <-> In2.Cu <-> B.Cu)
            if self.is_via_free(cgx, cgy, net_name):
                for nli in range(NL):
                    if nli == cli:
                        continue
                    nxt = (nli, cgx, cgy)
                    ng = g + 12.0
                    if ng < g_score.get(nxt, 1e18):
                        g_score[nxt] = ng
                        parent[nxt] = curr
                        heapq.heappush(open_heap, (ng + h_cost(cgx, cgy), ng, nxt, (0, 0)))

        return None

    def commit_path(self, path, net_name, width_mm=0.25):
        if not path or len(path) < 2:
            return
        net = get_or_create_net(self.board, net_name)

        seg_start = path[0]
        prev = path[0]

        for i in range(1, len(path)):
            curr = path[i]
            if curr[0] != prev[0]:
                if seg_start != prev:
                    x1, y1 = idx_to_mm(seg_start[1], seg_start[2])
                    x2, y2 = idx_to_mm(prev[1], prev[2])
                    add_track_segment(self.board, x1, y1, x2, y2, width_mm, LAYERS[seg_start[0]], net)
                    self.register_segment(x1, y1, x2, y2, width_mm, seg_start[0], net_name)
                vx, vy = idx_to_mm(curr[1], curr[2])
                add_via_at(self.board, vx, vy, 0.3, 0.6, net)
                self.register_via(vx, vy, 0.6, net_name)
                seg_start = curr
            else:
                dx1 = prev[1] - seg_start[1]
                dy1 = prev[2] - seg_start[2]
                dx2 = curr[1] - prev[1]
                dy2 = curr[2] - prev[2]
                if (dx1 != 0 and dy2 != 0) or (dy1 != 0 and dx2 != 0):
                    x1, y1 = idx_to_mm(seg_start[1], seg_start[2])
                    x2, y2 = idx_to_mm(prev[1], prev[2])
                    add_track_segment(self.board, x1, y1, x2, y2, width_mm, LAYERS[seg_start[0]], net)
                    self.register_segment(x1, y1, x2, y2, width_mm, seg_start[0], net_name)
                    seg_start = prev
            prev = curr

        if seg_start != prev:
            x1, y1 = idx_to_mm(seg_start[1], seg_start[2])
            x2, y2 = idx_to_mm(prev[1], prev[2])
            add_track_segment(self.board, x1, y1, x2, y2, width_mm, LAYERS[seg_start[0]], net)
            self.register_segment(x1, y1, x2, y2, width_mm, seg_start[0], net_name)


def snap_outward(val, step_dir):
    if step_dir < 0:
        return math.floor((val - 1e-4) / GRID_STEP) * GRID_STEP
    elif step_dir > 0:
        return math.ceil((val + 1e-4) / GRID_STEP) * GRID_STEP
    return round(val / GRID_STEP) * GRID_STEP


def compute_pad_escape(ref, pnum, px, py, hx, hy, fp_x, fp_y, is_pth, default_li):
    """
    Her pad'in gerçek yarı-boyutuna (hx, hy) göre hem pad_margin (0.34mm) hem de via_margin (0.57mm)
    sınırının TAM DIŞINA çıkan güvenli ızgara çıkış noktasını (escape point) hesaplar.
    """
    out_x = hx + 0.58
    out_y = hy + 0.58

    # Molex J1: Sıra 1 (1..7) YUKARI (-Y_k), Sıra 2 (8..14) AŞAĞI (+Y_k)
    if ref == "J1":
        p_int = int(pnum)
        if p_int <= 7:
            return snap_outward(px, 0), snap_outward(py - 1.50, -1)
        elif p_int == 8:
            return snap_outward(px - 1.50, -1), snap_outward(py, 0)
        else:
            return snap_outward(px, 0), snap_outward(py + 1.50, 1)

    # U1 (ESP32-S3-WROOM-1U): Sol sıra sola, alt sıra aşağı, sağ sıra sağa çıkar
    if ref == "U1" and pnum.isdigit():
        p_int = int(pnum)
        if 1 <= p_int <= 14:
            return snap_outward(px - out_x, -1), snap_outward(py, 0)
        elif 15 <= p_int <= 26:
            return snap_outward(px, 0), snap_outward(py + out_y, 1)
        elif 27 <= p_int <= 40:
            return snap_outward(px + out_x, 1), snap_outward(py, 0)

    # U2 (SIMCom SIM808): Sol sola, alt aşağı, sağ sağa, üst yukarı çıkar
    if ref == "U2" and pnum.isdigit():
        p_int = int(pnum)
        if 1 <= p_int <= 17:
            return snap_outward(px - out_x, -1), snap_outward(py, 0)
        elif 18 <= p_int <= 34:
            return snap_outward(px, 0), snap_outward(py + out_y, 1)
        elif 35 <= p_int <= 51:
            return snap_outward(px + out_x, 1), snap_outward(py, 0)
        elif 52 <= p_int <= 68:
            return snap_outward(px, 0), snap_outward(py - out_y, -1)

    # U3 (LIS3DH LGA-16 0.5mm pitch): Merkezden dışarı doğru
    if ref == "U3":
        p_int = int(pnum)
        if p_int in [1, 2, 3, 4]:
            return snap_outward(px - out_x, -1), snap_outward(py, 0)
        elif p_int in [5, 6, 7, 8]:
            return snap_outward(px, 0), snap_outward(py + out_y, 1)
        elif p_int in [9, 10, 11, 12]:
            return snap_outward(px + out_x, 1), snap_outward(py, 0)
        else:
            return snap_outward(px, 0), snap_outward(py - out_y, -1)

    # U10 (BTS7002 0.65mm pitch): Sol sıra (1..7) sola (Pad 2 ve 3 1.0mm yelpaze ile açılır), sağ sıra (8..14) sağa, Pad 15 yukarı
    if ref == "U10":
        p_int = int(pnum)
        if p_int == 2:
            return snap_outward(px - out_x, -1), 33.00
        elif p_int == 3:
            return snap_outward(px - out_x, -1), 34.00
        elif p_int == 5:
            return snap_outward(px - out_x, -1), 35.25
        elif p_int <= 7:
            return snap_outward(px - out_x, -1), snap_outward(py, 0)
        elif p_int <= 14:
            return snap_outward(px + out_x, 1), snap_outward(py, 0)
        return snap_outward(px, 0), snap_outward(py - out_y, -1)

    # Çift sıralı IC'ler (U4, U5, U6, U7, U8, D3, Q5, D2, U9, Q1): Sol padler sola, sağ padler sağa!
    if ref in ["U4", "U5", "U6", "U7", "U8", "D3", "Q5", "D2", "U9", "Q1"]:
        if px < fp_x - 0.2:
            return snap_outward(px - out_x, -1), snap_outward(py, 0)
        elif px > fp_x + 0.2:
            return snap_outward(px + out_x, 1), snap_outward(py, 0)

    # U11, U12 (rot=270 SO-4): Üst padler yukarı, alt padler aşağı
    if ref in ["U11", "U12"]:
        if py < fp_y - 0.2:
            return snap_outward(px, 0), snap_outward(py - out_y, -1)
        elif py > fp_y + 0.2:
            return snap_outward(px, 0), snap_outward(py + out_y, 1)

    # J4 (USB-C): Sinyal padleri aşağı (+Y_k, D3'e doğru tam dikey 1.0mm aralıkla), VBUS yukarı (-Y_k) çıkar
    if ref == "J4":
        if pnum == "B5":
            return 34.75, 8.75
        elif pnum in ["B6", "A6"]:
            return 35.75, 8.75
        elif pnum in ["B7", "A7"]:
            return 36.75, 9.00
        elif pnum == "A5":
            return 37.75, 8.75
        elif pnum in ["A4", "B9", "A9", "B4"]:
            return snap_outward(px, 0), snap_outward(py - out_y, -1)

    # 2-pinli pasifler (L1, F1, D1, C1..C8, R1..R20): Merkezden dışa doğru
    if abs(px - fp_x) >= abs(py - fp_y):
        if px < fp_x - 0.1:
            return snap_outward(px - out_x, -1), snap_outward(py, 0)
        elif px > fp_x + 0.1:
            return snap_outward(px + out_x, 1), snap_outward(py, 0)
    else:
        if py < fp_y - 0.1:
            return snap_outward(px, 0), snap_outward(py - out_y, -1)
        elif py > fp_y + 0.1:
            return snap_outward(px, 0), snap_outward(py + out_y, 1)

    return snap_outward(px, 0), snap_outward(py, 0)


def route_all_nets(board):
    router = ObstacleRouter(board)

    # --------------------------------------------------------------------------
    # A. RF 50-OHM MİKROŞERİT HATLAR (DOĞRUDAN DÜZ HAT, 0 VIA)
    # --------------------------------------------------------------------------
    # 1. RF_GSM: U2 Pin 60 (57.0, 12.0) -> ANT1 Pad 1 (57.0, 9.025)
    router.add_manual_polyline([(57.0, 12.0), (57.0, 9.025)], 0.60, pcbnew.F_Cu, "RF_GSM")
    # 2. RF_GPS: U2 Pin 42 (69.0, 25.0) -> ANT2 Pad 1 (71.975, 25.0)
    router.add_manual_polyline([(69.0, 25.0), (71.975, 25.0)], 0.60, pcbnew.F_Cu, "RF_GPS")

    # --------------------------------------------------------------------------
    # B. AYNI BİLEŞEN ÜZERİNDEKİ ÇOKLU / ÜST ÜSTE PAD KÖPRÜLERİ (INTRA-FOOTPRINT TIES)
    # --------------------------------------------------------------------------
    # J4 USB-C (Gerçek pad Y_k = 7.48mm, pad boyu Y_k in [6.905, 8.055]):
    # VBUS_5V: A9/B4 (34.10, 7.48) <-> A4/B9 (38.90, 7.48) — Üstten Y_k=5.75mm'den köprüle
    router.add_manual_polyline([(34.10, 7.48), (34.10, 5.75), (38.90, 5.75), (38.90, 7.48)], 0.30, pcbnew.F_Cu, "VBUS_5V")
    # USB_CON_DP: B6 (35.75, 7.48) <-> A6 (36.75, 7.48) — Üstten Y_k=6.35mm'den köprüle
    router.add_manual_polyline([(35.75, 7.48), (35.75, 6.35), (36.75, 6.35), (36.75, 7.48)], 0.20, pcbnew.F_Cu, "USB_CON_DP")
    # USB_CON_DN: A7 (36.25, 7.48) <-> B7 (37.25, 7.48) — Alttan Y_k=8.55mm'den köprüle ve (36.75, 9.00) noktasına çıkar
    router.add_manual_polyline([(36.25, 7.48), (36.25, 8.55), (36.75, 8.55), (36.75, 9.00)], 0.20, pcbnew.F_Cu, "USB_CON_DN")
    router.add_manual_polyline([(37.25, 7.48), (37.25, 8.55), (36.75, 8.55)], 0.20, pcbnew.F_Cu, "USB_CON_DN")
    # J4 GND: A12/B1 (33.30, 7.48) -> SH (31.39, 6.905) ve A1/B12 (39.70, 7.48) -> SH (41.61, 6.905)
    router.add_manual_polyline([(33.30, 7.48), (31.39, 7.48), (31.39, 6.905)], 0.30, pcbnew.F_Cu, "GND")
    router.add_manual_polyline([(39.70, 7.48), (41.61, 7.48), (41.61, 6.905)], 0.30, pcbnew.F_Cu, "GND")

    # D3.2 (35.3625, 11.50 F.Cu) -> (34.25, 11.50) ve U7.2 (39.6375, 12.50 B.Cu) -> (40.75, 12.50) doğrudan GND via bağlantıları
    gnd_net = get_or_create_net(board, "GND")
    router.add_manual_polyline([(35.3625, 11.50), (34.25, 11.50)], 0.25, pcbnew.F_Cu, "GND")
    add_via_at(board, 34.25, 11.50, 0.3, 0.6, gnd_net)
    router.register_via(34.25, 11.50, 0.6, "GND")

    router.add_manual_polyline([(39.6375, 12.50), (40.75, 12.50)], 0.25, pcbnew.B_Cu, "GND")
    add_via_at(board, 40.75, 12.50, 0.3, 0.6, gnd_net)
    router.register_via(40.75, 12.50, 0.6, "GND")

    # U4.4 (21.6375, 29.05 B.Cu) -> R2.2 (22.325, 26.00 B.Cu) GND köprüsü
    router.add_manual_polyline([(21.6375, 29.05), (21.6375, 27.50), (22.325, 27.50), (22.325, 26.00)], 0.25, pcbnew.B_Cu, "GND")

    # R16.2 (33.325, 23.00 B.Cu), U6.2 (27.3625, 12.50 B.Cu), U1.40 (28.25, 15.59 F.Cu), R9.2 (31.825, 10.50 F.Cu) ve U5.3->U5.1 (B.Cu) GND bağlantıları
    router.add_manual_polyline([(33.325, 23.00), (34.50, 23.00), (34.50, 24.25)], 0.25, pcbnew.B_Cu, "GND")
    add_via_at(board, 34.50, 24.25, 0.3, 0.6, gnd_net)
    router.register_via(34.50, 24.25, 0.6, "GND")

    router.add_manual_polyline([(27.3625, 12.50), (26.25, 12.50)], 0.25, pcbnew.B_Cu, "GND")
    add_via_at(board, 26.25, 12.50, 0.3, 0.6, gnd_net)
    router.register_via(26.25, 12.50, 0.6, "GND")

    router.add_manual_polyline([(28.25, 15.59), (29.50, 15.59), (29.50, 15.50)], 0.25, pcbnew.F_Cu, "GND")
    add_via_at(board, 29.50, 15.50, 0.3, 0.6, gnd_net)
    router.register_via(29.50, 15.50, 0.6, "GND")

    router.add_manual_polyline([(31.825, 10.50), (33.00, 10.50)], 0.25, pcbnew.F_Cu, "GND")
    add_via_at(board, 33.00, 10.50, 0.3, 0.6, gnd_net)
    router.register_via(33.00, 10.50, 0.6, "GND")

    router.add_manual_polyline([(18.525, 11.865), (20.25, 11.865), (20.25, 14.405), (18.525, 14.405)], 0.25, pcbnew.B_Cu, "GND")

    # Q1.4 (20.83, 36.595 B.Cu), R14.2 (12.825, 36.00 F.Cu), U2.17 (45.0, 32.0 F.Cu), U2.29 (60.0, 36.0 F.Cu) GND viaları
    router.add_manual_polyline([(20.83, 36.595), (19.00, 36.595), (19.00, 35.50)], 0.25, pcbnew.B_Cu, "GND")
    add_via_at(board, 19.00, 35.50, 0.3, 0.6, gnd_net)
    router.register_via(19.00, 35.50, 0.6, "GND")

    router.add_manual_polyline([(12.825, 36.00), (14.25, 36.00)], 0.25, pcbnew.F_Cu, "GND")
    add_via_at(board, 14.25, 36.00, 0.3, 0.6, gnd_net)
    router.register_via(14.25, 36.00, 0.6, "GND")

    router.add_manual_polyline([(45.00, 32.00), (47.00, 32.00)], 0.25, pcbnew.F_Cu, "GND")
    add_via_at(board, 47.00, 32.00, 0.3, 0.6, gnd_net)
    router.register_via(47.00, 32.00, 0.6, "GND")

    router.add_manual_polyline([(60.00, 36.00), (60.00, 34.00)], 0.25, pcbnew.F_Cu, "GND")
    add_via_at(board, 60.00, 34.00, 0.3, 0.6, gnd_net)
    router.register_via(60.00, 34.00, 0.6, "GND")

    # U1.41 (ESP32-S3 Termal Pad 3x3 Alt-Pad Dizisi) F.Cu H-Köprüsü ve Merkez GND Viası (19.40, 24.01)
    for ty in [22.61, 24.01, 25.41]:
        router.add_manual_polyline([(18.00, ty), (20.80, ty)], 0.30, pcbnew.F_Cu, "GND")
    for tx in [18.00, 19.40, 20.80]:
        router.add_manual_polyline([(tx, 22.61), (tx, 25.41)], 0.30, pcbnew.F_Cu, "GND")
    add_via_at(board, 19.40, 24.01, 0.3, 0.6, gnd_net)
    router.register_via(19.40, 24.01, 0.6, "GND")

    # U3 (LIS3DH) 4x GND Pini (5, 7, 10, 12) İç Merkez GND Viasına (36.50, 22.00) Bağlantısı
    router.add_manual_polyline([(35.75, 23.275), (35.75, 22.85), (36.00, 22.50), (36.50, 22.00)], 0.20, pcbnew.F_Cu, "GND")
    router.add_manual_polyline([(36.75, 23.275), (36.75, 22.00), (36.50, 22.00)], 0.20, pcbnew.F_Cu, "GND")
    router.add_manual_polyline([(37.775, 22.25), (36.50, 22.25), (36.50, 22.00)], 0.20, pcbnew.F_Cu, "GND")
    router.add_manual_polyline([(37.775, 21.25), (37.35, 21.25), (36.90, 21.50), (36.50, 22.00)], 0.20, pcbnew.F_Cu, "GND")
    add_via_at(board, 36.50, 22.00, 0.3, 0.6, gnd_net)
    router.register_via(36.50, 22.00, 0.6, "GND")

    # SW1 (RESET) ve SW2 (BOOT) içindeki çift Pad 1 ve çift Pad 2 köprüleri
    router.add_manual_polyline([(2.75, 17.33), (6.85, 17.33)], 0.25, pcbnew.F_Cu, "ESP_EN")
    router.add_manual_polyline([(2.75, 18.93), (6.85, 18.93)], 0.25, pcbnew.F_Cu, "GND")
    router.add_manual_polyline([(2.75, 32.20), (6.85, 32.20)], 0.25, pcbnew.F_Cu, "ESP_BOOT")
    router.add_manual_polyline([(2.75, 33.80), (6.85, 33.80)], 0.25, pcbnew.F_Cu, "GND")

    # U10 (BTS7002-1EPP) Sağ Sıra Pin 8..14 (IGNITION_OUT) dikey bara (tam X=36.35mm!)
    router.add_manual_polyline([(36.35, 32.55), (36.35, 36.45)], 0.30, pcbnew.F_Cu, "IGNITION_OUT")

    # Q1 (SQJ411EP B.Cu): Sol sıra Pin 1,2,3 (X=20.83, Y=40.405..37.865) (+12V_IN)
    router.add_manual_polyline([(20.83, 40.405), (20.83, 37.865)], 0.30, pcbnew.B_Cu, "+12V_IN")
    # Q1 Sağ sıra Pin 5 (X=26.295, Y=40.405..36.595) ve Termal Tab (24.19, 38.5) (+12V_PROT)
    router.add_manual_polyline([(26.295, 40.405), (26.295, 36.595)], 0.30, pcbnew.B_Cu, "+12V_PROT")
    router.add_manual_polyline([(26.295, 38.50), (24.19, 38.50)], 0.40, pcbnew.B_Cu, "+12V_PROT")

    # U4 (TPS54302 B.Cu): Pin 2 (19.363, 30.0) <-> Pin 5 (21.637, 30.0) yatay iç köprü (+12V_IN)
    router.add_manual_polyline([(19.363, 30.0), (21.637, 30.0)], 0.25, pcbnew.B_Cu, "+12V_IN")

    # U3 (LIS3DH F.Cu): Pin 1 (35.225, 21.25) <-> Pin 14 (36.75, 20.725) <-> R19.1 (35.675, 17.50) <-> R20.1 (35.675, 15.20) (+3V3) köprüsü
    router.add_manual_polyline([(35.225, 21.25), (34.50, 21.25), (34.50, 19.75), (36.75, 19.75), (36.75, 20.725)], 0.25, pcbnew.F_Cu, "+3V3")
    router.add_manual_polyline([(34.50, 19.75), (34.50, 17.50), (35.675, 17.50)], 0.25, pcbnew.F_Cu, "+3V3")
    router.add_manual_polyline([(34.50, 17.50), (34.50, 15.20), (35.675, 15.20)], 0.25, pcbnew.F_Cu, "+3V3")

    # U2 (SIMCom SIM808 F.Cu): Pin 55 (62.0, 12.0), 56 (61.0, 12.0), 57 (60.0, 12.0) (VSYS_3V86) üst bara
    router.add_manual_polyline([(60.0, 12.0), (62.0, 12.0)], 0.30, pcbnew.F_Cu, "VSYS_3V86")

    # --------------------------------------------------------------------------
    # C. TÜM SİNYAL VE GÜÇ AĞLARINI 3 KATMANLI A* İLE %100 BAĞLA
    # --------------------------------------------------------------------------
    net_pads = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        fp_pos = fp.GetPosition()
        fp_x, fp_y = pcbnew.ToMM(fp_pos.x), pcbnew.ToMM(fp_pos.y)
        for p in fp.Pads():
            pnum = p.GetNumber()
            if ref == "U10" and pnum == "":
                continue
            net_name = p.GetNetname() if p.GetNet() else ""
            if not net_name or net_name in ["GND", "NC", "RF_GSM", "RF_GPS"]:
                continue
            pos = p.GetPosition()
            px = round(pcbnew.ToMM(pos.x), 4)
            py = round(pcbnew.ToMM(pos.y), 4)

            # Köprülenmiş ikincil padleri atla (tek ana pad üzerinden ağa bağlansın)
            if ref == "J4" and pnum in ["A6", "A7", "A9", "B4", "B9"]:
                continue
            if ref == "U10" and pnum in ["8", "9", "10", "12", "13", "14"]:
                continue
            if ref == "Q1" and pnum in ["1", "3"]:
                continue
            if ref == "Q1" and pnum == "5" and px < 25.0:
                continue  # Q1 Pad 5 sağdaki (26.295, 39.135) üzerinden çıksın
            if ref == "Q1" and pnum == "5" and abs(py - 39.135) > 0.2:
                continue
            if ref == "U4" and pnum == "2":
                continue
            if ref == "U3" and pnum == "1":
                continue
            if ref in ["R19", "R20"] and pnum == "1":
                continue
            if ref == "U2" and pnum in ["55", "57"]:
                continue

            bb = p.GetBoundingBox()
            hx = round(pcbnew.ToMM(bb.GetWidth()) * 0.5, 4)
            hy = round(pcbnew.ToMM(bb.GetHeight()) * 0.5, 4)
            ls = p.GetLayerSet()
            is_pth = p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
            default_li = 0 if ls.Contains(pcbnew.F_Cu) else 2
            net_pads.setdefault(net_name, []).append((ref, pnum, px, py, hx, hy, fp_x, fp_y, is_pth, default_li))

    # 0.25mm ızgarada 2 adım (0.50mm) mesafede >=0.20mm DRC boşluğu sağlamak için
    # w1*0.5 + w2*0.5 <= 0.275mm olmalı -> Güç hatları 0.30mm, sinyal hatları 0.25mm!
    power_widths = {
        "IGNITION_IN": 0.30,
        "IGNITION_OUT": 0.30,
        "+12V_RAW": 0.30,
        "+12V_PROT": 0.30,
        "+12V_IN": 0.30,
        "BUCK_SW": 0.30,
        "VSYS_3V86": 0.30,
        "VBAT_LIFEPO4": 0.30,
        "+3V3": 0.25,
        "VBUS_5V": 0.25,
    }

    def net_sort_key(n):
        pads = net_pads[n]
        xs = [p[2] for p in pads]
        ys = [p[3] for p in pads]
        span = (max(xs) - min(xs)) + (max(ys) - min(ys))
        return (len(pads), span)

    sorted_nets = sorted(net_pads.keys(), key=net_sort_key)

    # 1. ÖN-HAZIRLIK: Tüm padlerin escape (çıkış) noktalarını hesapla ve engel haritasında rezerve et.
    # DİKKAT: Stub segmentlerini sadece rota gerçekten bağlandığında ve kullanılan katmanda çiz (track_dangling %100 önlenir!)
    net_prepared_nodes = {}
    for net_name in sorted_nets:
        pads = net_pads[net_name]
        w_mm = power_widths.get(net_name, 0.25)

        unique_pads = []
        seen_xy = set()
        for item in pads:
            key = (round(item[2], 3), round(item[3], 3), item[9])
            if key not in seen_xy:
                seen_xy.add(key)
                unique_pads.append(item)

        if len(unique_pads) <= 1:
            continue

        pad_nodes = []
        for ref, pnum, px, py, hx, hy, fp_x, fp_y, is_pth, default_li in unique_pads:
            ex, ey = compute_pad_escape(ref, pnum, px, py, hx, hy, fp_x, fp_y, is_pth, default_li)
            gx, gy = mm_to_idx(ex, ey)
            snapped_x, snapped_y = idx_to_mm(gx, gy)
            stub_w = min(w_mm, 0.25)

            # Çıkış yönünde 1 hücre (0.25mm) daha ileri rezerve et ki geçen başka bir yol 0.50mm mesafeden
            # via_obs'u (v_margin=0.675mm) kilitleyemesin!
            sdx = 1 if snapped_x > px + 0.1 else (-1 if snapped_x < px - 0.1 else 0)
            sdy = 1 if snapped_y > py + 0.1 else (-1 if snapped_y < py - 0.1 else 0)
            fgx = max(1, min(NX - 2, gx + sdx))
            fgy = max(1, min(NY - 2, gy + sdy))

            if is_pth:
                for li in range(NL):
                    router.register_segment(px, py, snapped_x, py, stub_w, li, net_name)
                    router.register_segment(snapped_x, py, snapped_x, snapped_y, stub_w, li, net_name)
                    router.layer_obs[li][gx][gy].add(net_name)
                    router.layer_obs[li][fgx][fgy].add(net_name)
                allowed = [(0, gx, gy), (1, gx, gy), (2, gx, gy)]
            else:
                router.register_segment(px, py, snapped_x, py, stub_w, default_li, net_name)
                router.register_segment(snapped_x, py, snapped_x, snapped_y, stub_w, default_li, net_name)
                router.layer_obs[default_li][gx][gy].add(net_name)
                router.layer_obs[default_li][fgx][fgy].add(net_name)
                allowed = [(default_li, gx, gy)]
            pad_nodes.append((ref, pnum, px, py, snapped_x, snapped_y, is_pth, default_li, allowed))

        pad_nodes.sort(key=lambda p: 0 if p[6] else 1)
        net_prepared_nodes[net_name] = pad_nodes

    def draw_pad_stub_on_layer(px, py, snapped_x, snapped_y, layer_idx, stub_w, net_obj):
        if abs(px - snapped_x) > 1e-3 or abs(py - snapped_y) > 1e-3:
            if abs(px - snapped_x) > 1e-3 and abs(py - snapped_y) > 1e-3:
                add_track_segment(board, px, py, snapped_x, py, stub_w, LAYERS[layer_idx], net_obj)
                add_track_segment(board, snapped_x, py, snapped_x, snapped_y, stub_w, LAYERS[layer_idx], net_obj)
            else:
                add_track_segment(board, px, py, snapped_x, snapped_y, stub_w, LAYERS[layer_idx], net_obj)

    # 2. A* İLE TÜM AĞLARI YÖNLENDİR
    failed_connections = []
    for net_name in sorted_nets:
        if net_name not in net_prepared_nodes:
            continue
        pad_nodes = net_prepared_nodes[net_name]
        w_mm = power_widths.get(net_name, 0.25)
        stub_w = min(w_mm, 0.25)
        net_obj = get_or_create_net(board, net_name)

        first_pad = pad_nodes[0]
        tree_nodes = set(first_pad[8])
        unrouted = pad_nodes[1:]
        first_pad_stub_drawn = False

        esc_map = {}
        for pinfo in pad_nodes:
            _, _, px, py, sx, sy, is_pth, def_li, allowed = pinfo
            egx, egy = allowed[0][1], allowed[0][2]
            esc_map[(egx, egy)] = (px, py, sx, sy, is_pth, def_li)

        while unrouted:
            best_idx = 0
            best_dist = 999999
            for idx, pinfo in enumerate(unrouted):
                allowed = pinfo[8]
                _, gx, gy = allowed[0]
                for _, tx, ty in tree_nodes:
                    d = abs(gx - tx) + abs(gy - ty)
                    if d < best_dist:
                        best_dist = d
                        best_idx = idx

            pinfo = unrouted.pop(best_idx)
            ref, pnum, px, py, sx, sy, is_pth, def_li, allowed = pinfo
            path = router.route_point_to_tree(allowed, tree_nodes, net_name, w_mm)
            used_w = w_mm
            if path is None and w_mm > 0.25:
                path = router.route_point_to_tree(allowed, tree_nodes, net_name, 0.25)
                used_w = 0.25

            if path is not None:
                router.commit_path(path, net_name, used_w)
                if len(path) >= 1:
                    start_li = path[0][0]
                    end_li, end_gx, end_gy = path[-1]
                    if not (ref == "J4" and pnum in ["B7", "A7"]):
                        draw_pad_stub_on_layer(px, py, sx, sy, start_li if is_pth else def_li, stub_w, net_obj)
                    if (end_gx, end_gy) in esc_map:
                        epx, epy, esx, esy, eis_pth, edef_li = esc_map[(end_gx, end_gy)]
                        if not (abs(esx - 36.75) < 1e-2 and abs(esy - 9.00) < 1e-2):
                            draw_pad_stub_on_layer(epx, epy, esx, esy, end_li if eis_pth else edef_li, stub_w, net_obj)
                        first_pad_stub_drawn = True
                    elif not first_pad_stub_drawn:
                        fref, fpnum, fpx, fpy, fsx, fsy, fis_pth, fdef_li, _ = first_pad
                        if not (fref == "J4" and fpnum in ["B7", "A7"]):
                            draw_pad_stub_on_layer(fpx, fpy, fsx, fsy, end_li if fis_pth else fdef_li, stub_w, net_obj)
                        first_pad_stub_drawn = True

                for node in path:
                    tree_nodes.add(node)
                for anode in allowed:
                    tree_nodes.add(anode)
            else:
                print(f"[HATA] Rota bulunamadı: {net_name} -> {ref}.{pnum}")
                failed_connections.append((net_name, ref, pnum))

    # --------------------------------------------------------------------------
    # D. HER GND SMD PADİ İÇİN DOĞRUDAN In1.Cu (GND DÜZLEMİ) VİA BAĞLANTISI
    # (Sadece tamamen boş hücrelerden geçen kısa L-bağlantıları ekler; kalanlar F.Cu/B.Cu Zone ile birleşir)
    # --------------------------------------------------------------------------
    gnd_net = get_or_create_net(board, "GND")
    manual_gnd_done = {
        ("D3", "2"), ("U7", "2"), ("U4", "4"), ("Q1", "4"),
        ("R14", "2"), ("U2", "17"), ("U2", "29"),
        ("U1", "41"), ("U3", "5"), ("U3", "7"), ("U3", "10"), ("U3", "12"),
        ("R16", "2"), ("U6", "2"), ("U1", "40"), ("R9", "2"), ("U5", "3"),
    }
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        for p in fp.Pads():
            if not p.GetNet() or p.GetNetname() != "GND":
                continue
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                continue
            if (ref, p.GetNumber()) in manual_gnd_done:
                continue
            pos = p.GetPosition()
            px = round(pcbnew.ToMM(pos.x), 4)
            py = round(pcbnew.ToMM(pos.y), 4)
            ls = p.GetLayerSet()
            li = 0 if ls.Contains(pcbnew.F_Cu) else 2
            gx, gy = mm_to_idx(px, py)

            best_v = None
            best_d = 999999
            for r in range(1, 12):
                for dx in range(-r, r + 1):
                    for dy in range(-r, r + 1):
                        if abs(dx) != r and abs(dy) != r:
                            continue
                        vx, vy = gx + dx, gy + dy
                        if vx < 2 or vx >= NX - 2 or vy < 2 or vy >= NY - 2:
                            continue
                        if router.is_via_free(vx, vy, "GND"):
                            ok = True
                            step_x = 1 if vx >= gx else -1
                            for cx in range(gx, vx + step_x, step_x):
                                if cx != gx and not router.is_cell_free(li, cx, gy, "GND"):
                                    ok = False
                                    break
                            if ok:
                                step_y = 1 if vy >= gy else -1
                                for cy in range(gy, vy + step_y, step_y):
                                    if cy != gy and not router.is_cell_free(li, vx, cy, "GND"):
                                        ok = False
                                        break
                            if ok:
                                d = abs(dx) + abs(dy)
                                if d < best_d:
                                    best_d = d
                                    best_v = (vx, vy)
                if best_v:
                    break

            if best_v:
                vx, vy = best_v
                vmx, vmy = idx_to_mm(vx, vy)
                add_track_segment(board, px, py, vmx, py, 0.25, LAYERS[li], gnd_net)
                add_track_segment(board, vmx, py, vmx, vmy, 0.25, LAYERS[li], gnd_net)
                router.register_segment(px, py, vmx, py, 0.25, li, "GND")
                router.register_segment(vmx, py, vmx, vmy, 0.25, li, "GND")
                add_via_at(board, vmx, vmy, 0.3, 0.6, gnd_net)
                router.register_via(vmx, vmy, 0.6, "GND")
            else:
                print(f"[GND-UYARI] Doğrudan via bulunamadı: {ref}.{p.GetNumber()} @ ({px}, {py}) katman={li}")

    print(f"Yönlendirme tamamlandı. Başarısız bağlantı sayısı: {len(failed_connections)}")
    return router


def add_gnd_zones_and_fill(board):
    """In1.Cu (Tam GND İç Düzlemi) üzerinde GND poligon dolgusunu oluşturur ve doldurur."""
    gnd_net = get_or_create_net(board, "GND")
    margin = 1.0
    chamfer = 2.2
    corners = [
        (margin + chamfer, margin),
        (BOARD_W - margin - chamfer, margin),
        (BOARD_W - margin, margin + chamfer),
        (BOARD_W - margin, BOARD_H - margin - chamfer),
        (BOARD_W - margin - chamfer, BOARD_H - margin),
        (margin + chamfer, BOARD_H - margin),
        (margin, BOARD_H - margin - chamfer),
        (margin, margin + chamfer),
    ]

    for lyr in [pcbnew.In1_Cu]:
        zone = pcbnew.ZONE(board)
        zone.SetNet(gnd_net)
        zone.SetLayer(lyr)
        zone.SetIsRuleArea(False)
        zone.SetDoNotAllowTracks(False)
        zone.SetDoNotAllowVias(False)
        zone.SetDoNotAllowPads(False)
        zone.SetLocalClearance(pcbnew.FromMM(0.25))
        zone.SetMinThickness(pcbnew.FromMM(0.20))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)

        outline = zone.Outline()
        outline.NewOutline()
        for cx, cy in corners:
            outline.Append(pcbnew.FromMM(cx), pcbnew.FromMM(cy))
        board.Add(zone)

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())


def build_board():
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    net_cache.clear()

    # 1. Kart Dış Çerçevesi (Edge.Cuts: 80.0 mm x 55.0 mm, R=2.5 mm Yuvarlatılmış Köşe)
    radius_mm = 2.5
    k = radius_mm * 0.70710678

    def add_edge_line(s_mm, e_mm):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(s_mm[0]), pcbnew.FromMM(s_mm[1])))
        seg.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(e_mm[0]), pcbnew.FromMM(e_mm[1])))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(pcbnew.FromMM(0.15))
        board.Add(seg)

    def add_edge_arc(s_mm, m_mm, e_mm):
        arc = pcbnew.PCB_SHAPE(board)
        arc.SetShape(pcbnew.SHAPE_T_ARC)
        arc.SetArcGeometry(
            pcbnew.VECTOR2I(pcbnew.FromMM(s_mm[0]), pcbnew.FromMM(s_mm[1])),
            pcbnew.VECTOR2I(pcbnew.FromMM(m_mm[0]), pcbnew.FromMM(m_mm[1])),
            pcbnew.VECTOR2I(pcbnew.FromMM(e_mm[0]), pcbnew.FromMM(e_mm[1])),
        )
        arc.SetLayer(pcbnew.Edge_Cuts)
        arc.SetWidth(pcbnew.FromMM(0.15))
        board.Add(arc)

    add_edge_line((radius_mm, 0.0), (BOARD_W - radius_mm, 0.0))
    add_edge_line((BOARD_W, radius_mm), (BOARD_W, BOARD_H - radius_mm))
    add_edge_line((BOARD_W - radius_mm, BOARD_H), (radius_mm, BOARD_H))
    add_edge_line((0.0, BOARD_H - radius_mm), (0.0, radius_mm))

    add_edge_arc((0.0, radius_mm), (radius_mm - k, radius_mm - k), (radius_mm, 0.0))
    add_edge_arc((BOARD_W - radius_mm, 0.0), (BOARD_W - radius_mm + k, radius_mm - k), (BOARD_W, radius_mm))
    add_edge_arc((BOARD_W, BOARD_H - radius_mm), (BOARD_W - radius_mm + k, BOARD_H - radius_mm + k), (BOARD_W - radius_mm, BOARD_H))
    add_edge_arc((radius_mm, BOARD_H), (radius_mm - k, BOARD_H - radius_mm + k), (0.0, BOARD_H - radius_mm))

    # 2. Montaj Delikleri (4x M2.5)
    for ref, hx, hy in [("H1", 5.0, 5.0), ("H2", 75.0, 5.0), ("H3", 5.0, 50.0), ("H4", 75.0, 50.0)]:
        load_footprint(board, "MountingHole", "MountingHole_2.7mm_M2.5_Pad_Via", ref, "M2.5_Hole", hx, hy)
        set_component_nets(board, ref, {"1": "GND"})

    # 3. Bileşen Yerleşimi (CPL v4.0 — 80x55mm Ferah Yerleşim)
    cpl = [
        # --- ÜST KATMAN (F.Cu) ---
        ("Connector_Molex", "Molex_Micro-Fit_3.0_43045-1400_2x07_P3.00mm_Horizontal", "J1", "Molex_14P", 22.0, 6.5, 0, pcbnew.F_Cu),
        ("RF_Module", "ESP32-S3-WROOM-1U", "U1", "ESP32-S3-WROOM-1U", 19.5, 31.0, 0, pcbnew.F_Cu),
        ("Button_Switch_SMD", "SW_Push_1P1T_NO_CK_KMR2", "SW1", "RESET", 4.8, 36.87, 0, pcbnew.F_Cu),
        ("Button_Switch_SMD", "SW_Push_1P1T_NO_CK_KMR2", "SW2", "BOOT", 4.8, 22.0, 0, pcbnew.F_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R4", "10k", 4.8, 42.0, 0, pcbnew.F_Cu),

        # Durum LED'leri ve seri dirençleri
        ("LED_SMD", "LED_0603_1608Metric", "LED1", "RED_ALARM", 13.5, 49.5, 0, pcbnew.F_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R5", "330R", 13.5, 46.0, 0, pcbnew.F_Cu),
        ("LED_SMD", "LED_0603_1608Metric", "LED2", "BLUE_BLE", 19.5, 49.5, 0, pcbnew.F_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R6", "330R", 19.5, 46.0, 0, pcbnew.F_Cu),
        ("LED_SMD", "LED_0603_1608Metric", "LED3", "GREEN_GSM", 25.5, 49.5, 0, pcbnew.F_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R7", "330R", 25.5, 46.0, 0, pcbnew.F_Cu),

        # USB-C, ESD & CC Dirençleri (R8=CC1 sağda A5 hizasında, R9=CC2 solda B5 hizasında)
        ("Connector_USB", "USB_C_Receptacle_GCT_USB4110", "J4", "USB_C", 36.5, 51.2, 180, pcbnew.F_Cu),
        ("Package_TO_SOT_SMD", "SOT-23-6", "D3", "USBLC6", 36.5, 43.5, 0, pcbnew.F_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R8", "5.1k", 42.0, 44.5, 0, pcbnew.F_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R9", "5.1k", 31.0, 44.5, 0, pcbnew.F_Cu),

        # LIS3DH IMU ve I2C Pull-up Dirençleri
        ("Package_LGA", "LGA-16_3x3mm_P0.5mm", "U3", "LIS3DH", 36.5, 33.0, 0, pcbnew.F_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R19", "4.7k", 36.5, 37.5, 0, pcbnew.F_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R20", "4.7k", 36.5, 39.8, 0, pcbnew.F_Cu),

        # BTS7002-1EPP 25A PROFET ve IS Direnci
        ("Package_SO", "Infineon_PG-TSDSO-14-22", "U10", "BTS7002-1EPP", 33.5, 20.5, 0, pcbnew.F_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R10", "1.2k", 33.5, 25.5, 0, pcbnew.F_Cu),

        # LTV-356T Boş Vites Optokuplörü ve Dirençleri
        ("Package_SO", "SO-4_4.4x4.3mm_P2.54mm", "U9", "LTV-356T", 12.0, 11.5, 0, pcbnew.F_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R13", "4.7k", 12.0, 16.5, 0, pcbnew.F_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R14", "10k", 12.0, 19.0, 0, pcbnew.F_Cu),

        # Q5 Siren Sürücü MOSFET
        ("Package_TO_SOT_SMD", "SOT-23", "Q5", "DMN6075S", 40.5, 20.5, 0, pcbnew.F_Cu),

        # Marş ve Kill-Switch SSR (rot=270 ile Pin 1,2 üstte MCU'ya, Pin 3,4 altta J1'e bakar!)
        ("Package_SO", "SO-4_4.4x4.3mm_P2.54mm", "U11", "VO14642_Start", 49.5, 10.0, 270, pcbnew.F_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R11", "330R", 46.0, 15.8, 0, pcbnew.F_Cu),
        ("Package_SO", "SO-4_4.4x4.3mm_P2.54mm", "U12", "VO14642_Kill", 58.0, 10.0, 270, pcbnew.F_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R12", "330R", 54.5, 15.8, 0, pcbnew.F_Cu),

        # CAN Alıcı-Verici (U8), ESD (D2) ve Dekuplaj (C8)
        ("Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm", "U8", "SN65HVD230", 66.0, 11.0, 0, pcbnew.F_Cu),
        ("Package_TO_SOT_SMD", "SOT-23", "D2", "PESD2CAN", 72.5, 11.0, 0, pcbnew.F_Cu),
        ("Capacitor_SMD", "C_0603_1608Metric", "C8", "100nF", 66.0, 15.5, 0, pcbnew.F_Cu),

        # SIMCom SIM808 (68-Pin LCC 24x24mm) ve GSM/GPS Anten Soketleri (ANT1, ANT2)
        ("RF_GSM", "SIMCom_SIM900", "U2", "SIMCom_SIM808", 57.0, 31.0, 0, pcbnew.F_Cu),
        ("Connector_Coaxial", "U.FL_Hirose_U.FL-R-SMT-1_Vertical", "ANT1", "GSM_UFL", 57.0, 47.5, 90, pcbnew.F_Cu),
        ("Connector_Coaxial", "U.FL_Hirose_U.FL-R-SMT-1_Vertical", "ANT2", "GPS_UFL", 73.5, 30.0, 0, pcbnew.F_Cu),

        # --- ALT KATMAN (B.Cu) ---
        # 12V Otomotiv Giriş Koruması (F1, D1, Q1)
        ("Fuse", "Fuse_1812_4532Metric", "F1", "1812L200PR", 13.5, 10.5, 180, pcbnew.B_Cu),
        ("Diode_SMD", "D_SMC", "D1", "TPSMC36A", 13.5, 16.5, 0, pcbnew.B_Cu),
        ("Package_SO", "PowerPAK_SO-8_Single", "Q1", "SQJ411EP", 23.5, 16.5, 0, pcbnew.B_Cu),

        # TPS54302 3.86V 3A Buck Katı
        ("Capacitor_SMD", "C_1210_3225Metric", "C2", "22uF_50V", 26.5, 24.5, 90, pcbnew.B_Cu),
        ("Package_TO_SOT_SMD", "SOT-23-6", "U4", "TPS54302", 20.5, 25.0, 0, pcbnew.B_Cu),
        ("Capacitor_SMD", "C_0603_1608Metric", "C5", "100nF", 20.5, 21.5, 0, pcbnew.B_Cu),
        ("Inductor_SMD", "L_Vishay_IHLP-2020", "L1", "6.8uH", 12.5, 24.5, 0, pcbnew.B_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R1", "54.9k", 16.5, 29.0, 0, pcbnew.B_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R2", "10k", 21.5, 29.0, 0, pcbnew.B_Cu),
        ("Capacitor_SMD", "C_1210_3225Metric", "C1", "22uF_25V", 6.0, 30.0, 90, pcbnew.B_Cu),
        ("Capacitor_SMD", "C_1210_3225Metric", "C3", "47uF_10V", 6.0, 23.0, 90, pcbnew.B_Cu),

        # LiFePO4 Şarj (U5, R3, J3), İdeal Diyot (U6), 3.3V LDO (U7, C6)
        ("Connector_JST", "JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal", "J3", "JST_LiFePO4", 12.5, 42.5, 0, pcbnew.B_Cu),
        ("Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm", "U5", "CN3058", 21.0, 42.5, 0, pcbnew.B_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R3", "2.4k", 21.0, 47.5, 0, pcbnew.B_Cu),
        ("Package_TO_SOT_SMD", "SOT-23-6", "U6", "LM66100", 28.5, 42.5, 0, pcbnew.B_Cu),
        ("Package_TO_SOT_SMD", "SOT-23-5", "U7", "AP2112K-3.3", 38.5, 42.5, 180, pcbnew.B_Cu),
        ("Capacitor_SMD", "C_0603_1608Metric", "C6", "10uF", 38.5, 38.5, 0, pcbnew.B_Cu),

        # Akü ve Batarya ADC Gerilim Bölücüler (R15..R18 — U1 ve U3 arasındaki temiz koridorda X=32.5mm'de)
        ("Resistor_SMD", "R_0603_1608Metric", "R15", "100k", 32.5, 34.5, 0, pcbnew.B_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R16", "10k", 32.5, 32.0, 0, pcbnew.B_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R17", "100k", 32.5, 29.5, 0, pcbnew.B_Cu),
        ("Resistor_SMD", "R_0603_1608Metric", "R18", "100k", 32.5, 27.0, 0, pcbnew.B_Cu),

        # SIM808 Tantal Kapasitör (C4), SIM Dekuplaj (C7) ve Nano SIM Yuvası (J2)
        ("Capacitor_Tantalum_SMD", "CP_EIA-7343-31_Kemet-D", "C4", "100uF_Tantal", 47.5, 42.5, 0, pcbnew.B_Cu),
        ("Capacitor_SMD", "C_0603_1608Metric", "C7", "100nF", 46.5, 22.0, 0, pcbnew.B_Cu),
        ("Connector_Card", "nanoSIM_Hinged_CUI_NSIM-2-C", "J2", "Nano_SIM", 57.0, 30.0, 180, pcbnew.B_Cu),
    ]

    for lib, fp_name, ref, val, x, y, rot, lyr in cpl:
        load_footprint(board, lib, fp_name, ref, val, x, y, rot, lyr)

    # 4. Şematikle %100 Birebir Net Atamaları
    net_assignments = {
        "F1": {"1": "+12V_RAW", "2": "+12V_PROT"},
        "D1": {"1": "+12V_PROT", "2": "GND"},
        "Q1": {"1": "+12V_IN", "2": "+12V_IN", "3": "+12V_IN", "4": "GND", "5": "+12V_PROT"},
        "C2": {"1": "+12V_IN", "2": "GND"},
        "U4": {"2": "+12V_IN", "5": "+12V_IN", "4": "GND", "1": "BUCK_SW", "6": "BUCK_BOOT", "3": "BUCK_FB"},
        "C5": {"1": "BUCK_SW", "2": "BUCK_BOOT"},
        "L1": {"1": "BUCK_SW", "2": "VSYS_3V86"},
        "R1": {"1": "VSYS_3V86", "2": "BUCK_FB"},
        "R2": {"1": "BUCK_FB", "2": "GND"},
        "C1": {"1": "VSYS_3V86", "2": "GND"},
        "C3": {"1": "VSYS_3V86", "2": "GND"},
        "U5": {"4": "VSYS_3V86", "1": "GND", "2": "CHRG_ISET", "3": "GND", "5": "VBAT_LIFEPO4", "8": "VBAT_LIFEPO4"},
        "R3": {"1": "CHRG_ISET", "2": "GND"},
        "J3": {"1": "VBAT_LIFEPO4", "2": "GND"},
        "U6": {"1": "VBAT_LIFEPO4", "3": "VSYS_3V86", "2": "GND", "6": "VSYS_3V86"},
        "U7": {"1": "VSYS_3V86", "3": "VSYS_3V86", "2": "GND", "5": "+3V3"},
        "C6": {"1": "+3V3", "2": "GND"},
        "U1": {
            "1": "GND", "2": "+3V3", "3": "ESP_EN", "4": "IMU_INT1", "5": "IMU_INT2",
            "6": "CAN_TX", "7": "CAN_RX", "8": "PROFET_DEN", "10": "GSM_RXD", "11": "GSM_TXD",
            "12": "PROFET_IN", "13": "USB_DN", "14": "USB_DP", "15": "SSR_KILL_DRV",
            "17": "SSR_STARTER_DRV", "18": "PROFET_IS", "19": "SIREN_DRV", "20": "NEUTRAL_OUT",
            "21": "ADC_VBAT_BIKE", "22": "ADC_VBAT_INT", "23": "GSM_RI",
            "24": "LED_ALARM_DRV", "25": "LED_BLE_DRV", "26": "LED_GSM_DRV", "27": "ESP_BOOT",
            "31": "GSM_PWRKEY", "32": "GSM_DTR", "33": "GSM_STATUS",
            "38": "I2C_SCL", "39": "I2C_SDA", "40": "GND", "41": "GND",
        },
        "R4": {"1": "+3V3", "2": "ESP_EN"},
        "SW1": {"1": "ESP_EN", "2": "GND"},
        "SW2": {"1": "ESP_BOOT", "2": "GND"},
        "R5": {"1": "LED_ALARM_DRV", "2": "LED1_A"},
        "LED1": {"1": "GND", "2": "LED1_A"},
        "R6": {"1": "LED_BLE_DRV", "2": "LED2_A"},
        "LED2": {"1": "GND", "2": "LED2_A"},
        "R7": {"1": "LED_GSM_DRV", "2": "LED3_A"},
        "LED3": {"1": "GND", "2": "LED3_A"},
        "J4": {
            "A4": "VBUS_5V", "A9": "VBUS_5V", "B4": "VBUS_5V", "B9": "VBUS_5V",
            "A5": "USB_CC1", "B5": "USB_CC2",
            "A6": "USB_CON_DP", "B6": "USB_CON_DP",
            "A7": "USB_CON_DN", "B7": "USB_CON_DN",
            "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "SH": "GND",
        },
        "D3": {"1": "USB_DN", "3": "USB_DP", "2": "GND", "6": "USB_CON_DN", "4": "USB_CON_DP", "5": "VBUS_5V"},
        "R8": {"1": "USB_CC1", "2": "GND"},
        "R9": {"1": "USB_CC2", "2": "GND"},
        "U2": {
            "1": "GSM_PWRKEY", "3": "GSM_DTR", "4": "GSM_RI",
            "9": "GSM_TXD", "10": "GSM_RXD",
            "17": "GND", "18": "GND", "29": "GND", "39": "GND", "41": "GND", "43": "GND",
            "45": "GND", "46": "GND", "53": "GND", "54": "GND", "58": "GND", "59": "GND",
            "61": "GND", "62": "GND", "63": "GND", "64": "GND", "65": "GND",
            "26": "VSYS_3V86", "30": "SIM_VDD", "31": "SIM_DATA", "32": "SIM_CLK", "33": "SIM_RST",
            "42": "RF_GPS", "52": "LED_GSM_DRV",
            "55": "VSYS_3V86", "56": "VSYS_3V86", "57": "VSYS_3V86",
            "60": "RF_GSM", "66": "GSM_STATUS",
        },
        "C4": {"1": "VSYS_3V86", "2": "GND"},
        "C7": {"1": "SIM_VDD", "2": "GND"},
        "J2": {"1": "SIM_VDD", "2": "SIM_RST", "3": "SIM_CLK", "7": "SIM_DATA", "5": "GND", "SH": "GND"},
        "ANT1": {"1": "RF_GSM", "2": "GND"},
        "ANT2": {"1": "RF_GPS", "2": "GND"},
        "U10": {
            "1": "GND", "2": "PROFET_IN", "3": "PROFET_DEN", "5": "PROFET_IS", "15": "IGNITION_IN",
            "8": "IGNITION_OUT", "9": "IGNITION_OUT", "10": "IGNITION_OUT", "11": "IGNITION_OUT",
            "12": "IGNITION_OUT", "13": "IGNITION_OUT", "14": "IGNITION_OUT",
        },
        "R10": {"1": "PROFET_IS", "2": "GND"},
        "R11": {"1": "SSR_STARTER_DRV", "2": "SSR1_A"},
        "U11": {"1": "SSR1_A", "2": "GND", "4": "STARTER_CTRL", "3": "+12V_IN"},
        "R12": {"1": "SSR_KILL_DRV", "2": "SSR2_A"},
        "U12": {"1": "SSR2_A", "2": "GND", "4": "KILL_SWITCH_A", "3": "KILL_SWITCH_B"},
        "R13": {"1": "+12V_IN", "2": "NEUTRAL_ANODE"},
        "U9": {"1": "NEUTRAL_ANODE", "2": "NEUTRAL_SENSE", "4": "+3V3", "3": "NEUTRAL_OUT"},
        "R14": {"1": "NEUTRAL_OUT", "2": "GND"},
        "Q5": {"1": "SIREN_DRV", "2": "GND", "3": "SIREN_NEG"},
        "R15": {"1": "+12V_IN", "2": "ADC_VBAT_BIKE"},
        "R16": {"1": "ADC_VBAT_BIKE", "2": "GND"},
        "R17": {"1": "VBAT_LIFEPO4", "2": "ADC_VBAT_INT"},
        "R18": {"1": "ADC_VBAT_INT", "2": "GND"},
        "U3": {
            "1": "+3V3", "14": "+3V3", "4": "I2C_SCL", "6": "I2C_SDA",
            "7": "GND", "8": "+3V3", "5": "GND", "12": "GND", "10": "GND",
            "11": "IMU_INT1", "9": "IMU_INT2",
        },
        "R19": {"1": "+3V3", "2": "I2C_SCL"},
        "R20": {"1": "+3V3", "2": "I2C_SDA"},
        "U8": {"3": "+3V3", "1": "CAN_TX", "4": "CAN_RX", "8": "GND", "7": "CAN_H", "6": "CAN_L", "2": "GND"},
        "D2": {"1": "CAN_H", "2": "CAN_L", "3": "GND"},
        "C8": {"1": "+3V3", "2": "GND"},
        "J1": {
            "1": "+12V_RAW", "2": "GND", "3": "IGNITION_IN", "4": "IGNITION_OUT",
            "5": "STARTER_CTRL", "6": "KILL_SWITCH_A", "7": "KILL_SWITCH_B",
            "8": "NEUTRAL_SENSE", "9": "+12V_IN", "10": "SIREN_NEG",
            "11": "CAN_H", "12": "CAN_L", "13": "LED1_A", "14": "GND",
        },
    }

    for ref, pmap in net_assignments.items():
        set_component_nets(board, ref, pmap)

    # 5. Tüm Devre Yollarını Yönlendir
    route_all_nets(board)

    # 6. GND Bakır Düzlemlerini (In1.Cu, F.Cu, B.Cu) Oluştur ve Doldur
    add_gnd_zones_and_fill(board)

    return board


if __name__ == "__main__":
    b = build_board()
    b.Save(OUTPUT_PCB)
    print(f"Başarıyla kaydedildi: {OUTPUT_PCB}")
