# -*- coding: utf-8 -*-
"""Gate-3 (implementability) per STEP5E_GATE2_INFERENCE.md §6, Codex-specified design.

Question: is the W1-DRO frontier extension past SAA's empirical sample-max ceiling
(targets in the ~57-63 day region) a REAL industrial decision, or only mathematically
reachable? Test each real plant-origin target against ORIGIN-SPECIFIC, HISTORY-ONLY
capacity benchmarks. Any rule can pass by adding safety stock, so Gate-3 is necessary,
not sufficient; it only rules OUT the extension if targets are historically unreachable.

Faithful to the 5 fixes:
1. Corrected replenishment eqn: R^req_{t+1} = max(0, S_{t+1} + Dhat_{t+1} - I_t).
   EIA sees deliveries not orders -> we claim only "historical deliverability of the
   target," not full order-policy implementability.
2. ALL benchmarks origin-specific & history-only (rolling window strictly before origin;
   full-sample max would be leakage inside Gate-3 itself).
3. Three separate constraints: gross delivery throughput (receipts vs p90/max);
   net stock-building rate (required build vs historical receipts-burn / positive dInv);
   storage envelope (target tons vs historical stock-tons max).
4. Days vs tons separated (if burn falls, same tons = more days).
5. Three-way classification per target: Routine-demonstrated (<p90) /
   Exceptional-demonstrated (p90-max) / Unsupported-by-history (>max); targets
   57/60/63 d; plus min months to build target at p90/max net-build rate.

Units: matches backtest_v2 (inv_days = k*30, k in monthly-mean-burn units).
target_tons(D) = (D/30) * mean_monthly_burn_train.
"""
import json, numpy as np
from collections import defaultdict, Counter

WIN = 48                      # rolling training window (months), same as backtest
MIN_OBS = 24                  # min positive-burn months in window
DAY_TARGETS = [57, 60, 63]    # frontier-extension day targets past SAA ~56d ceiling
SAA_CEIL_DAYS = 56            # empirical SAA sample-max ceiling from Gate-1/2


def pctl(a, q):
    a = np.asarray(a, float)
    return float(np.percentile(a, q)) if len(a) else float('nan')


def main():
    raw = json.load(open('coal_panel_2015_2024.json'))
    P = defaultdict(list)
    for kk, v in raw.items():
        p, y, m = kk.split('|')
        P[p].append((int(y), int(m), v['stock'], v['burn'], v['recv']))
    for p in P:
        P[p].sort()

    # per-plant month-indexed dicts
    S = {}
    for p, seq in P.items():
        b = np.array([x[3] if x[3] else 0.0 for x in seq], float)
        if (b > 0).sum() < 36:
            continue
        S[p] = {(y, m): dict(stock=s, burn=bb, recv=r) for (y, m, s, bb, r) in seq}
    allmonths = sorted({ym for p in S for ym in S[p]})
    origins = list(range(WIN, len(allmonths) - 1))

    # results accumulator per day-target
    rows = {D: [] for D in DAY_TARGETS}
    n_eval = 0

    for t0i in origins:
        train_ms = allmonths[t0i - WIN + 1:t0i + 1]   # window incl. decision month t
        t_ym = allmonths[t0i]                          # decision month t (end)
        test_ym = allmonths[t0i + 1]                   # target month t+1
        for p, dd in S.items():
            # window burn (positive) for mean burn
            wb = [dd[ym]['burn'] for ym in train_ms if ym in dd and dd[ym]['burn'] > 0]
            if len(wb) < MIN_OBS or t_ym not in dd:
                continue
            mbm = float(np.mean(wb))                    # mean monthly burn (train)
            if mbm <= 0:
                continue
            if dd[t_ym]['stock'] is None or dd[t_ym]['stock'] <= 0:
                continue                                 # need a real decision-month inventory
            I_t = float(dd[t_ym]['stock'])              # inventory at decision month t
            Dhat = mbm                                  # mean-forecast next-month burn
            # SAA operating target (95% service), tons, history-only — comparator for ΔR^req
            S_saa = float(np.quantile(wb, 0.95))
            R_req_saa = max(0.0, S_saa + Dhat - I_t)

            # history-only benchmark series over the window (strictly <= t)
            recv_hist = np.array([dd[ym]['recv'] for ym in train_ms
                                  if ym in dd and dd[ym]['recv'] is not None and dd[ym]['recv'] > 0], float)
            stock_hist = np.array([dd[ym]['stock'] for ym in train_ms
                                   if ym in dd and dd[ym]['stock'] is not None and dd[ym]['stock'] > 0], float)
            # net-build: monthly (recv - burn), positive part
            nb = []
            dstk = []
            prev = None
            for ym in train_ms:
                if ym in dd:
                    r = dd[ym]['recv'] or 0.0
                    bth = dd[ym]['burn'] or 0.0
                    nb.append(r - bth)
                    s = dd[ym]['stock']
                    if prev is not None and s is not None and prev is not None:
                        dstk.append(s - prev)
                    prev = s
            nb = np.array(nb, float)
            nb_pos = nb[nb > 0]
            dstk = np.array(dstk, float)
            dstk_pos = dstk[dstk > 0]
            if len(recv_hist) < 12 or len(stock_hist) < 12 or len(nb_pos) < 6:
                continue

            # benchmarks
            recv_p90, recv_max = pctl(recv_hist, 90), float(recv_hist.max())
            stock_p90, stock_max = pctl(stock_hist, 90), float(stock_hist.max())
            nb_p90, nb_max = pctl(nb_pos, 90), float(nb_pos.max())
            # days-of-burn history (tons / (mbm/30) = tons*30/mbm), using window mean burn as ref
            days_hist = stock_hist * 30.0 / mbm
            days_p90, days_max = pctl(days_hist, 90), float(days_hist.max())

            n_eval_this = True
            for D in DAY_TARGETS:
                target_tons = (D / 30.0) * mbm             # target inventory in tons
                # required next-month receipts to hit target after burning Dhat
                R_req = max(0.0, target_tons + Dhat - I_t)
                # required one-month net build to raise inventory to target
                need_build = max(0.0, target_tons - I_t)   # = R_req - Dhat if positive

                # three-way classification helper
                def classify(x, p90, mx):
                    if x <= p90:
                        return 'Routine'
                    if x <= mx:
                        return 'Exceptional'
                    return 'Unsupported'

                cls_storage = classify(target_tons, stock_p90, stock_max)      # storage envelope (tons)
                cls_days = classify(D, days_p90, days_max)                       # days-of-burn envelope
                cls_recv = classify(R_req, recv_p90, recv_max)                   # gross throughput
                cls_nb = classify(need_build, nb_p90, nb_max)                    # net stock-building in 1 mo

                # ---- Codex correction: 'extension as a NEW ACTION' = ΔR^req > 0 vs SAA target ----
                new_action = R_req > R_req_saa + 1e-6 * mbm
                build_pos = target_tons > I_t
                # applicability-aware classes: storage demonstrated if already holding >= target;
                # net-build N/A if no positive build; throughput always applies when R_req>0
                cls_storage_c = 'Routine' if I_t >= target_tons else classify(target_tons, stock_p90, stock_max)
                cls_nb_c = classify(need_build, nb_p90, nb_max) if build_pos else None
                cls_recv_c = classify(R_req, recv_p90, recv_max)
                order = {'Routine': 0, 'Exceptional': 1, 'Unsupported': 2}
                applic = [cls_storage_c, cls_recv_c] + ([cls_nb_c] if cls_nb_c else [])
                binding_c = max(applic, key=lambda c: order[c])
                dR = R_req - R_req_saa                                            # extra receipts vs SAA

                # min months to build target at p90 / max net-build rate
                mm_p90 = need_build / nb_p90 if nb_p90 > 0 else float('inf')
                mm_max = need_build / nb_max if nb_max > 0 else float('inf')

                rows[D].append(dict(
                    plant=p, t=str(t_ym), target=str(test_ym),
                    mbm=mbm, I_t=I_t, target_tons=target_tons, R_req=R_req, need_build=need_build,
                    cls_storage=cls_storage, cls_days=cls_days, cls_recv=cls_recv, cls_nb=cls_nb,
                    min_months_p90=mm_p90, min_months_max=mm_max,
                    already_above=I_t >= target_tons,
                    new_action=new_action, dR=dR, binding_c=binding_c,
                    build_pos=build_pos, S_saa=S_saa, saa_ge_target=S_saa >= target_tons,
                ))
            if n_eval_this:
                n_eval += 1

    # ---- report ----
    report = dict(meta=dict(win=WIN, n_plant_origins=n_eval, day_targets=DAY_TARGETS,
                            saa_ceil_days=SAA_CEIL_DAYS), per_target={})
    print(f"plant-origins evaluated (unique p x t): {n_eval}")
    print(f"total target-rows per day-target: {len(rows[DAY_TARGETS[0]])}\n")

    for D in DAY_TARGETS:
        rr = rows[D]
        Ntot = len(rr)
        already = sum(r['already_above'] for r in rr)         # inventory already at/above target
        # binding classification = worst across the three ACTIONABLE constraints
        # (storage=can the pile physically hold it; net-build=can it be built in 1 mo; throughput=can receipts arrive)
        def binding(r):
            order = {'Routine': 0, 'Exceptional': 1, 'Unsupported': 2}
            worst = max([r['cls_storage'], r['cls_nb'], r['cls_recv']], key=lambda c: order[c])
            return worst
        bind_counts = Counter(binding(r) for r in rr)
        stor_counts = Counter(r['cls_storage'] for r in rr)
        nb_counts = Counter(r['cls_nb'] for r in rr)
        recv_counts = Counter(r['cls_recv'] for r in rr)
        days_counts = Counter(r['cls_days'] for r in rr)
        # min-months distribution among those needing a build
        need = [r for r in rr if r['need_build'] > 0]
        # needer-restricted binding: the honest denominator for "extension as a NEW action"
        bind_need = Counter(binding(r) for r in need)
        Nneed = len(need)
        mmp90 = np.array([r['min_months_p90'] for r in need if np.isfinite(r['min_months_p90'])])
        # fraction needing >1 month even at p90 build rate
        frac_multi = float((mmp90 > 1.0).mean()) if len(mmp90) else float('nan')

        def frac(c, tot):
            return round(100.0 * c / tot, 1) if tot else 0.0

        print(f"===== target = {D} days =====  (N={Ntot} target-rows)")
        print(f"  already at/above target (no build needed): {already} ({frac(already,Ntot)}%)")
        print(f"  BINDING (worst of storage/net-build/throughput):")
        for k in ['Routine', 'Exceptional', 'Unsupported']:
            print(f"      {k:12s}: {bind_counts.get(k,0):5d} ({frac(bind_counts.get(k,0),Ntot)}%)")
        print(f"  storage-envelope (target tons vs hist stock): "
              f"R={frac(stor_counts.get('Routine',0),Ntot)}% "
              f"E={frac(stor_counts.get('Exceptional',0),Ntot)}% "
              f"U={frac(stor_counts.get('Unsupported',0),Ntot)}%")
        print(f"  net-build 1-mo   (need vs hist recv-burn+): "
              f"R={frac(nb_counts.get('Routine',0),Ntot)}% "
              f"E={frac(nb_counts.get('Exceptional',0),Ntot)}% "
              f"U={frac(nb_counts.get('Unsupported',0),Ntot)}%")
        print(f"  throughput       (R_req vs hist receipts):   "
              f"R={frac(recv_counts.get('Routine',0),Ntot)}% "
              f"E={frac(recv_counts.get('Exceptional',0),Ntot)}% "
              f"U={frac(recv_counts.get('Unsupported',0),Ntot)}%")
        print(f"  days-of-burn env (D vs hist days):           "
              f"R={frac(days_counts.get('Routine',0),Ntot)}% "
              f"E={frac(days_counts.get('Exceptional',0),Ntot)}% "
              f"U={frac(days_counts.get('Unsupported',0),Ntot)}%")
        # ---- Codex-corrected denominator: ΔR^req>0 (extension demands MORE receipts than SAA) ----
        # ALL cuts below use the SAME applicability-aware binding_c so subsets are nested-consistent.
        newact = [r for r in rr if r['new_action']]
        Nnew = len(newact)
        moot = Ntot - Nnew                                   # I_t >= S_D + Dhat -> both give 0 receipts
        bind_new = Counter(r['binding_c'] for r in newact)
        saa_ge = sum(r['saa_ge_target'] for r in rr)          # SAA already prescribes >= target (extension not beyond SAA)
        # intersection: genuine pile-BUILD AND a real new action, consistent classifier
        buildnew = [r for r in newact if r['build_pos']]
        Nbn = len(buildnew)
        bind_bn = Counter(r['binding_c'] for r in buildnew)
        maint = [r for r in newact if not r['build_pos']]     # new action but no positive build = MAINTENANCE
        Nmt = len(maint)
        bind_mt = Counter(r['binding_c'] for r in maint)
        mm_bn = np.array([r['min_months_p90'] for r in buildnew if np.isfinite(r['min_months_p90'])])
        frac_multi_bn = float((mm_bn > 1.0).mean()) if len(mm_bn) else float('nan')
        print(f"  --- CODEX-CORRECTED: NEW ACTION = ΔR^req>0 vs SAA (N={Nnew}; moot={moot} [{frac(moot,Ntot)}%]; SAA-already>=target={saa_ge}) ---")
        for k in ['Routine', 'Exceptional', 'Unsupported']:
            print(f"      binding* {k:12s}: {bind_new.get(k,0):5d} ({frac(bind_new.get(k,0),Nnew)}%)")
        print(f"    MAINTENANCE (new action, target<=I_t, N={Nmt}): "
              f"R={frac(bind_mt.get('Routine',0),Nmt)}% E={frac(bind_mt.get('Exceptional',0),Nmt)}% "
              f"U={frac(bind_mt.get('Unsupported',0),Nmt)}%")
        print(f"    PILE-BUILD  (new action, target> I_t, N={Nbn}): "
              f"R={frac(bind_bn.get('Routine',0),Nbn)}% E={frac(bind_bn.get('Exceptional',0),Nbn)}% "
              f"U={frac(bind_bn.get('Unsupported',0),Nbn)}%  "
              f">1mo@p90={round(100*frac_multi_bn,1) if np.isfinite(frac_multi_bn) else 'na'}%")
        # nested-consistency assertion (subset Unsupported <= superset Unsupported)
        assert bind_bn.get('Unsupported',0) + bind_mt.get('Unsupported',0) == bind_new.get('Unsupported',0), \
            "maint+build Unsupported must equal new-action Unsupported"
        print(f"  among rows needing a build: {len(need)}; "
              f"fraction needing >1 month even at p90 net-build rate: "
              f"{round(100*frac_multi,1) if np.isfinite(frac_multi) else 'na'}%")
        print(f"  min-months-to-build @p90 (needers): median={np.median(mmp90):.2f} "
              f"p90={np.percentile(mmp90,90):.2f}  max={mmp90.max():.2f}" if len(mmp90) else "  (no builders)")
        print()

        report['per_target'][str(D)] = dict(
            N=Ntot, already_above=already,
            binding={k: bind_counts.get(k, 0) for k in ['Routine', 'Exceptional', 'Unsupported']},
            storage={k: stor_counts.get(k, 0) for k in ['Routine', 'Exceptional', 'Unsupported']},
            net_build={k: nb_counts.get(k, 0) for k in ['Routine', 'Exceptional', 'Unsupported']},
            throughput={k: recv_counts.get(k, 0) for k in ['Routine', 'Exceptional', 'Unsupported']},
            days_env={k: days_counts.get(k, 0) for k in ['Routine', 'Exceptional', 'Unsupported']},
            n_needing_build=len(need),
            binding_needers={k: bind_need.get(k, 0) for k in ['Routine', 'Exceptional', 'Unsupported']},
            n_new_action=Nnew, n_moot=moot, n_saa_ge_target=saa_ge,
            binding_new_action={k: bind_new.get(k, 0) for k in ['Routine', 'Exceptional', 'Unsupported']},
            n_maintenance=Nmt, binding_maintenance={k: bind_mt.get(k, 0) for k in ['Routine', 'Exceptional', 'Unsupported']},
            n_pilebuild=Nbn, binding_pilebuild={k: bind_bn.get(k, 0) for k in ['Routine', 'Exceptional', 'Unsupported']},
            frac_multi_month_p90_pilebuild=frac_multi_bn,
            frac_multi_month_p90=frac_multi,
            min_months_p90_median=float(np.median(mmp90)) if len(mmp90) else None,
            min_months_p90_p90=float(np.percentile(mmp90, 90)) if len(mmp90) else None,
        )

    json.dump(report, open('gate3_report.json', 'w'), indent=1)
    print("saved gate3_report.json")


if __name__ == '__main__':
    main()
