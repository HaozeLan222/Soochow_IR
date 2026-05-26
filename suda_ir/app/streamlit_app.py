from __future__ import annotations

from pathlib import Path

import streamlit as st

from suda_ir.data.storage import load_jsonl
from suda_ir.ir.searcher import TutorSearcher


st.set_page_config(page_title="苏州大学导师检索", layout="wide")
st.title("苏州大学导师信息检索")

data_path = st.sidebar.text_input("数据文件", "data/sample/teachers.jsonl")
top_k = st.sidebar.slider("返回数量", 1, 20, 5)
field = st.sidebar.selectbox("查询类型", ["all", "name", "college"], format_func=lambda x: {
    "all": "综合查询",
    "name": "姓名",
    "college": "学院",
}[x])

query = st.text_input("输入查询条件", placeholder="例如：自然语言处理、周国栋、知识图谱")

if query:
    if not Path(data_path).exists():
        st.error(f"数据文件不存在：{data_path}")
        st.stop()
    docs = load_jsonl(data_path)
    searcher = TutorSearcher(docs)
    results = searcher.search(query, top_k=top_k, field=field)
    st.caption(f"共返回 {len(results)} 条结果")
    for rank, result in enumerate(results, start=1):
        doc = result.doc
        with st.container(border=True):
            st.subheader(f"{rank}. {doc.name or '未知姓名'}")
            st.write(f"学院：{doc.college or '未知'}")
            st.write(f"职称：{doc.title or '未知'}")
            st.write(f"相关度：{result.score:.4f}")
            if doc.research:
                st.write(f"研究方向：{doc.research}")
            if doc.profile:
                st.write(f"简介：{doc.profile[:300]}")
            if doc.url:
                st.link_button("教师主页", doc.url)

