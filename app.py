# 將篩選工具列寬度限制在「金剛指標」按鈕右邊界附近（9 欄中的前 4 欄寬度）
  st.markdown(
      """
      <style>
        .gold-indicator-limit {
            width: 44.4% !important;
            max-width: 44.4% !important;
            margin-top: 3px !important;
            margin-bottom: 4px !important;
        }
        .gold-indicator-limit [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: space-between !important;
            gap: 4px !important;
            flex-wrap: nowrap !important;
            width: 100% !important;
            margin-bottom: 0px !important;
        }
        .gold-indicator-limit [data-testid="column"] {
            flex: 0 0 auto !important;
            width: auto !important;
            min-width: 0 !important;
            padding: 0 !important;
        }
        .gold-status-text {
            color: #F0B84B;
            font-size: 10.5px;
            font-weight: 700;
            line-height: 24px;
            height: 24px;
            white-space: nowrap;
            display: inline-flex;
            align-items: center;
            margin-right: 1px;
        }
        .gold-tag-box {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            height: 24px;
            min-height: 24px;
            padding: 0 5px;
            border-radius: 3px;
            font-size: 10.5px;
            font-weight: 700;
            line-height: 24px;
            white-space: nowrap;
            box-sizing: border-box;
        }
        .gold-tag-idle {
            background-color: #14181f;
            color: #E2E8F0;
            border: 1px solid #3a4554;
        }
        .gold-tag-active {
            background-color: rgba(56, 178, 196, 0.22);
            color: #38B2C4;
            border: 1px solid #38B2C4;
        }
        .gold-indicator-limit [data-baseweb="select"] > div {
            min-height: 24px !important;
            height: 24px !important;
            font-size: 10.5px !important;
            line-height: 22px !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            padding-left: 5px !important;
            padding-right: 16px !important;
        }
        .gold-day-sel [data-baseweb="select"] {
            width: 40px !important;
            min-width: 40px !important;
        }
        .gold-vol-sel [data-baseweb="select"] {
            width: 54px !important;
            min-width: 54px !important;
        }
        .gold-val-sel [data-baseweb="select"] {
            width: 46px !important;
            min-width: 46px !important;
        }
        .gold-refresh-btn button {
            height: 24px !important;
            min-height: 24px !important;
            padding: 0 6px !important;
            font-size: 10.5px !important;
            line-height: 22px !important;
            white-space: nowrap !important;
        }
      </style>
      """,
      unsafe_allow_html=True,
  )

  st.markdown('<div class="gold-indicator-limit">', unsafe_allow_html=True)
  f_cols = st.columns([2.6, 0.65, 0.85, 0.9, 0.55, 0.8, 0.85])

  with f_cols[0]:
    st.markdown(
        f'<div class="gold-status-text">【{active_strategy_label}｜{selected_tf}】目前符合條件共 {matched_count} 檔標的。</div>',
        unsafe_allow_html=True,
    )

  with f_cols[1]:
    st.markdown('<div class="gold-day-sel">', unsafe_allow_html=True)
    selected_tf = st.selectbox(
        "週期",
        options=["日", "周"],
        index=0 if selected_tf == "日" else 1,
        key="gold_tf_select",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

  with f_cols[2]:
    vol_active_cls = "gold-tag-active" if vol_threshold > 0 else "gold-tag-idle"
    st.markdown(
        f'<div class="gold-tag-box {vol_active_cls}">成交量&gt;</div>',
        unsafe_allow_html=True,
    )

  with f_cols[3]:
    st.markdown('<div class="gold-vol-sel">', unsafe_allow_html=True)
    vol_threshold = st.selectbox(
        "成交量門檻",
        options=[0, 500, 1000, 2000, 3000, 5000, 10000],
        index=[0, 500, 1000, 2000, 3000, 5000, 10000].index(vol_threshold)
        if vol_threshold in [0, 500, 1000, 2000, 3000, 5000, 10000]
        else 3,
        key="gold_vol_select",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

  with f_cols[4]:
    val_active_cls = "gold-tag-active" if val_threshold > 0 else "gold-tag-idle"
    st.markdown(
        f'<div class="gold-tag-box {val_active_cls}">值&gt;</div>',
        unsafe_allow_html=True,
    )

  with f_cols[5]:
    st.markdown('<div class="gold-val-sel">', unsafe_allow_html=True)
    val_threshold = st.selectbox(
        "值門檻",
        options=[0, 0.8, 1.0, 1.2, 1.4, 1.6, 2.0],
        index=[0, 0.8, 1.0, 1.2, 1.4, 1.6, 2.0].index(val_threshold)
        if val_threshold in [0, 0.8, 1.0, 1.2, 1.4, 1.6, 2.0]
        else 4,
        key="gold_val_select",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

  with f_cols[6]:
    st.markdown('<div class="gold-refresh-btn">', unsafe_allow_html=True)
    if st.button("🔄 重整", key="gold_refresh_btn"):
      st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

  st.markdown("</div>", unsafe_allow_html=True)