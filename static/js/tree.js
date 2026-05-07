/**
 * tree.js — D3.js v7 树形图渲染
 * 提供 renderFamilyTree(data, containerSelector) 函数
 * data 格式: { member_id, name, gender, birth_year, generation, children: [...] }
 */

function renderFamilyTree(data, containerSelector) {
    const container = document.querySelector(containerSelector);
    container.innerHTML = '';
    if (!data) {
        container.innerHTML = '<div class="empty-state">无数据</div>';
        return;
    }

    const margin = { top: 20, right: 40, bottom: 20, left: 40 };
    const nodeWidth = 140;
    const nodeHeight = 60;
    const levelHeight = 120;

    // 构建 D3 hierarchy
    const root = d3.hierarchy(data);
    const treeLayout = d3.tree().nodeSize([nodeWidth + 20, levelHeight]);
    treeLayout(root);

    // 计算 SVG 尺寸
    const nodes = root.descendants();
    const xs = nodes.map(n => n.x);
    const ys = nodes.map(n => n.y);
    const minX = Math.min(...xs) - nodeWidth / 2 - margin.left;
    const maxX = Math.max(...xs) + nodeWidth / 2 + margin.right;
    const minY = Math.min(...ys) - margin.top;
    const maxY = Math.max(...ys) + nodeHeight + margin.bottom;

    const width  = maxX - minX;
    const height = maxY - minY;

    const svg = d3.select(container)
        .append('svg')
        .attr('width',  Math.max(width,  container.clientWidth  || 800))
        .attr('height', Math.max(height, 400))
        .style('background', 'transparent');

    const g = svg.append('g')
        .attr('transform', `translate(${-minX}, ${-minY})`);

    // ── 连接线 ───────────────────────────────────────────────
    g.selectAll('.link')
        .data(root.links())
        .enter().append('path')
        .attr('class', 'link')
        .attr('d', d3.linkVertical()
            .x(d => d.x)
            .y(d => d.y + nodeHeight / 2))
        .attr('fill', 'none')
        .attr('stroke', '#30363d')
        .attr('stroke-width', 1.5);

    // ── 节点组 ───────────────────────────────────────────────
    const node = g.selectAll('.node')
        .data(nodes)
        .enter().append('g')
        .attr('class', 'node')
        .attr('transform', d => `translate(${d.x - nodeWidth / 2}, ${d.y})`);

    // 节点背景矩形
    node.append('rect')
        .attr('width', nodeWidth)
        .attr('height', nodeHeight)
        .attr('rx', 8)
        .attr('fill', d => d.data.gender === 'M'
            ? 'rgba(41,58,90,0.9)'
            : 'rgba(80,35,55,0.9)')
        .attr('stroke', d => d.data.gender === 'M' ? '#4a7fc1' : '#c17a9a')
        .attr('stroke-width', 1.5)
        .style('cursor', 'pointer')
        .on('click', (evt, d) => {
            location.href = `/member/${d.data.member_id}`;
        });

    // 性别图标
    node.append('text')
        .attr('x', 10)
        .attr('y', 22)
        .attr('font-size', '14px')
        .text(d => d.data.gender === 'M' ? '♂' : '♀')
        .attr('fill', d => d.data.gender === 'M' ? '#4a7fc1' : '#c17a9a');

    // 姓名
    node.append('text')
        .attr('x', nodeWidth / 2)
        .attr('y', 25)
        .attr('text-anchor', 'middle')
        .attr('font-size', '13px')
        .attr('font-weight', '600')
        .attr('fill', '#e6edf3')
        .attr('font-family', 'Noto Serif SC, sans-serif')
        .text(d => d.data.name.length > 6 ? d.data.name.slice(0, 5) + '…' : d.data.name);

    // 出生年
    node.append('text')
        .attr('x', nodeWidth / 2)
        .attr('y', 44)
        .attr('text-anchor', 'middle')
        .attr('font-size', '11px')
        .attr('fill', '#8b949e')
        .text(d => d.data.birth_year ? `${d.data.birth_year}年生` : `第${d.data.generation}代`);

    // ID 标签
    node.append('text')
        .attr('x', nodeWidth - 6)
        .attr('y', 56)
        .attr('text-anchor', 'end')
        .attr('font-size', '10px')
        .attr('fill', '#484f58')
        .text(d => `#${d.data.member_id}`);

    // ── 缩放与拖拽 ─────────────────────────────────────────
    const zoom = d3.zoom()
        .scaleExtent([0.2, 3])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        });
    svg.call(zoom);

    // 初始居中
    const svgW = parseFloat(svg.attr('width'));
    const svgH = parseFloat(svg.attr('height'));
    const initialX = svgW / 2 - root.x;
    const initialY = 20;
    svg.call(zoom.transform, d3.zoomIdentity.translate(initialX, initialY));
}
