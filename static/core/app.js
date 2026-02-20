/**
 * Blood Lab - Frontend JavaScript
 * Chart rendering, upload handling, and UI interactions.
 */

/* ===== Theme Management ===== */

function getTheme() {
    return document.documentElement.getAttribute('data-theme') || 'dark';
}

function getCSSVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function initTheme() {
    var saved = localStorage.getItem('blood-lab-theme');
    if (!saved) {
        saved = 'dark';
    }
    document.documentElement.setAttribute('data-theme', saved);
}

function toggleTheme() {
    var current = getTheme();
    var next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('blood-lab-theme', next);
    // Re-read colors and re-render all charts
    updateChartColors();
    reRenderAllCharts();
}

// Apply theme immediately (before DOM ready) to prevent flash
initTheme();


/* ===== Chart Configuration ===== */

function getChartColors() {
    var isDark = getTheme() === 'dark';
    return {
        blue: getCSSVar('--accent-blue') || (isDark ? 'rgba(59, 130, 246, 1)' : 'rgba(37, 99, 235, 1)'),
        blueBg: isDark ? 'rgba(59, 130, 246, 0.15)' : 'rgba(37, 99, 235, 0.1)',
        blueGlow: isDark ? 'rgba(59, 130, 246, 0.4)' : 'rgba(37, 99, 235, 0.2)',
        green: getCSSVar('--accent-green') || (isDark ? 'rgba(16, 185, 129, 1)' : 'rgba(5, 150, 105, 1)'),
        greenBg: isDark ? 'rgba(16, 185, 129, 0.15)' : 'rgba(5, 150, 105, 0.1)',
        red: getCSSVar('--accent-red') || (isDark ? 'rgba(239, 68, 68, 1)' : 'rgba(220, 38, 38, 1)'),
        redBg: isDark ? 'rgba(239, 68, 68, 0.15)' : 'rgba(220, 38, 38, 0.1)',
        yellow: getCSSVar('--accent-yellow') || (isDark ? 'rgba(245, 158, 11, 1)' : 'rgba(217, 119, 6, 1)'),
        yellowBg: isDark ? 'rgba(245, 158, 11, 0.15)' : 'rgba(217, 119, 6, 0.1)',
        purple: getCSSVar('--accent-purple') || (isDark ? 'rgba(139, 92, 246, 1)' : 'rgba(124, 58, 237, 1)'),
        purpleBg: isDark ? 'rgba(139, 92, 246, 0.15)' : 'rgba(124, 58, 237, 0.1)',
        text: getCSSVar('--chart-text') || (isDark ? 'rgba(160, 160, 176, 1)' : 'rgba(74, 85, 104, 1)'),
        grid: getCSSVar('--chart-grid') || (isDark ? 'rgba(42, 42, 58, 0.5)' : 'rgba(226, 232, 240, 0.8)'),
        white: getCSSVar('--text-primary') || (isDark ? 'rgba(232, 232, 237, 1)' : 'rgba(26, 26, 46, 1)'),
        tooltipBg: getCSSVar('--tooltip-bg') || (isDark ? 'rgba(26, 26, 36, 0.95)' : 'rgba(255, 255, 255, 0.97)'),
        tooltipTitle: isDark ? '#e8e8ed' : '#1a1a2e',
        tooltipBody: isDark ? '#a0a0b0' : '#4a5568',
        pointBorder: getCSSVar('--point-border') || (isDark ? '#1a1a24' : '#ffffff'),
        gradientTop: isDark ? 'rgba(59, 130, 246, 0.3)' : 'rgba(37, 99, 235, 0.15)',
        gradientBottom: isDark ? 'rgba(59, 130, 246, 0.02)' : 'rgba(37, 99, 235, 0.01)',
        refBandBg: isDark ? 'rgba(16, 185, 129, 0.08)' : 'rgba(5, 150, 105, 0.06)',
        refLine: isDark ? 'rgba(16, 185, 129, 0.5)' : 'rgba(5, 150, 105, 0.4)',
        gaugeBg: isDark ? 'rgba(42, 42, 58, 0.8)' : 'rgba(226, 232, 240, 0.8)',
        gaugeNormal: isDark ? 'rgba(16, 185, 129, 0.3)' : 'rgba(5, 150, 105, 0.2)',
    };
}

var chartColors = getChartColors();

function updateChartColors() {
    chartColors = getChartColors();
    chartDefaults.plugins.tooltip.backgroundColor = chartColors.tooltipBg;
    chartDefaults.plugins.tooltip.titleColor = chartColors.tooltipTitle;
    chartDefaults.plugins.tooltip.bodyColor = chartColors.tooltipBody;
    chartDefaults.plugins.tooltip.borderColor = chartColors.blue;
    chartDefaults.scales.x.ticks.color = chartColors.text;
    chartDefaults.scales.x.grid.color = chartColors.grid;
    chartDefaults.scales.y.ticks.color = chartColors.text;
    chartDefaults.scales.y.grid.color = chartColors.grid;
}

var chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { display: false },
        tooltip: {
            backgroundColor: chartColors.tooltipBg,
            titleColor: chartColors.tooltipTitle,
            bodyColor: chartColors.tooltipBody,
            borderColor: chartColors.blue,
            borderWidth: 1,
            padding: 12,
            cornerRadius: 10,
            titleFont: { weight: '600' },
        },
    },
    scales: {
        x: {
            ticks: { color: chartColors.text, font: { size: 11 } },
            grid: { color: chartColors.grid },
        },
        y: {
            ticks: { color: chartColors.text, font: { size: 11 } },
            grid: { color: chartColors.grid },
        },
    },
};

/* ===== Chart Re-render on Theme Change ===== */

var _dashboardChartData = null;
var _categoryHealthData = null;
var _normalCountData = 0;
var _abnormalCountData = 0;
var _criticalBiomarkersData = null;
var _biomarkerDetailData = null;

function reRenderAllCharts() {
    // Destroy all existing Chart.js instances
    Object.keys(Chart.instances).forEach(function(key) {
        Chart.instances[key].destroy();
    });

    // Re-render dashboard charts
    if (_dashboardChartData && Object.keys(_dashboardChartData).length > 0) {
        renderDashboardCharts(_dashboardChartData);
    }
    if (_categoryHealthData && Object.keys(_categoryHealthData).length > 0) {
        renderRadarChart('radarChart', _categoryHealthData);
    }
    if (_normalCountData + _abnormalCountData > 0) {
        renderDonutChart('donutChart', _normalCountData, _abnormalCountData);
    }
    if (_criticalBiomarkersData && _criticalBiomarkersData.length > 0) {
        renderGaugeCharts('gaugesGrid', _criticalBiomarkersData);
        renderDeviationBars('deviationChart', _criticalBiomarkersData);
    }
    // Re-render biomarker detail chart
    if (_biomarkerDetailData) {
        renderBiomarkerChart('biomarkerChart', _biomarkerDetailData);
    }
}


/* ===== Category Labels ===== */

var categoryLabels = {
    'hemograma': 'Hemograma',
    'lipidograma': 'Lipidograma',
    'hepatica': 'F. Hep\u00e1tica',
    'renal': 'F. Renal',
    'glicemia': 'Glicemia',
    'hormonal': 'Hormonal',
    'tireoide': 'Tire\u00f3ide',
    'vitaminas': 'Vitaminas',
    'outros': 'Outros',
};


/* ===== Dashboard Charts ===== */

function renderDashboardCharts(data) {
    _dashboardChartData = data;
    var container = document.getElementById('chartsGrid');
    if (!container) return;

    container.innerHTML = '';

    // Group biomarkers by category
    var groups = {};
    var codes = Object.keys(data);
    codes.forEach(function(code) {
        var bm = data[code];
        if (bm.dates.length < 1) return;
        var cat = bm.category || 'Outros';
        if (!groups[cat]) groups[cat] = [];
        groups[cat].push({ code: code, bm: bm });
    });

    // Category display order
    var categoryOrder = [
        'Hemograma', 'Lipidograma', 'Fun\u00e7\u00e3o Hep\u00e1tica', 'Fun\u00e7\u00e3o Renal',
        'Glicemia', 'Hormonal', 'Tireoide', 'Inflama\u00e7\u00e3o', 'Prote\u00ednas',
        'Vitaminas e Minerais'
    ];

    // Render each category
    var sortedCats = Object.keys(groups).sort(function(a, b) {
        var ia = categoryOrder.indexOf(a);
        var ib = categoryOrder.indexOf(b);
        if (ia === -1) ia = 999;
        if (ib === -1) ib = 999;
        return ia - ib;
    });

    sortedCats.forEach(function(cat) {
        var items = groups[cat];

        // Category header
        var header = document.createElement('div');
        header.className = 'charts-category-header';
        header.innerHTML = '<h3>' + cat + '</h3><span class="charts-category-count">' + items.length + ' biomarcadores</span>';
        container.appendChild(header);

        // Charts grid for this category
        var grid = document.createElement('div');
        grid.className = 'charts-grid';

        items.forEach(function(item) {
            var code = item.code;
            var bm = item.bm;

            var cardUrl = window.location.pathname.replace(/\/$/, '') + '/biomarker/' + code + '/';

            var card = document.createElement('div');
            card.className = 'chart-card';
            card.style.cursor = 'pointer';
            card.setAttribute('data-biomarker-code', code);
            card.addEventListener('click', (function(url) {
                return function(e) {
                    if (_compareMode) return;
                    window.location.href = url;
                };
            })(cardUrl));

            var link = document.createElement('a');
            link.href = cardUrl;
            link.style.textDecoration = 'none';
            link.style.color = 'inherit';
            link.style.display = 'block';
            link.addEventListener('click', function(e) {
                if (_compareMode) e.preventDefault();
            });

            // Title with trend indicator
            var titleRow = document.createElement('div');
            titleRow.className = 'chart-title-row';

            var title = document.createElement('h4');
            title.textContent = bm.name + ' (' + bm.unit + ')';

            var trend = document.createElement('span');
            trend.className = 'chart-trend';
            if (bm.values.length >= 2) {
                var lastVal = bm.values[bm.values.length - 1];
                var prevVal = bm.values[bm.values.length - 2];
                var pctChange = ((lastVal - prevVal) / prevVal * 100).toFixed(1);
                if (pctChange > 0) {
                    trend.innerHTML = '<span class="trend-up">\u2191 +' + pctChange + '%</span>';
                } else if (pctChange < 0) {
                    trend.innerHTML = '<span class="trend-down">\u2193 ' + pctChange + '%</span>';
                } else {
                    trend.innerHTML = '<span class="trend-stable">\u2192 0%</span>';
                }
            }

            titleRow.appendChild(title);
            titleRow.appendChild(trend);
            link.appendChild(titleRow);

            // Last value annotation
            var lastValue = document.createElement('div');
            lastValue.className = 'chart-last-value';
            var lastV = bm.values[bm.values.length - 1];
            var isAbn = bm.is_abnormal && bm.is_abnormal[bm.is_abnormal.length - 1];
            lastValue.innerHTML = '<span class="' + (isAbn ? 'value-abnormal' : 'value-normal') + '">' + lastV + '</span> <span class="value-unit">' + bm.unit + '</span>';
            link.appendChild(lastValue);

            var chartContainer = document.createElement('div');
            chartContainer.className = 'chart-container';

            var canvas = document.createElement('canvas');
            chartContainer.appendChild(canvas);
            link.appendChild(chartContainer);
            card.appendChild(link);
            grid.appendChild(card);

            createSmallChart(canvas, bm);
        });

        container.appendChild(grid);
    });
}

function createSmallChart(canvas, data) {
    // Create gradient fill
    var ctx = canvas.getContext('2d');
    var gradient = ctx.createLinearGradient(0, 0, 0, 240);
    gradient.addColorStop(0, chartColors.gradientTop);
    gradient.addColorStop(1, chartColors.gradientBottom);

    // Point colors based on abnormal status
    var pointColors = [];
    var pointBorderColors = [];
    if (data.is_abnormal) {
        for (var i = 0; i < data.is_abnormal.length; i++) {
            if (data.is_abnormal[i]) {
                pointColors.push(chartColors.yellow);
                pointBorderColors.push(chartColors.yellow);
            } else {
                pointColors.push(chartColors.blue);
                pointBorderColors.push(chartColors.blue);
            }
        }
    } else {
        pointColors = chartColors.blue;
        pointBorderColors = chartColors.blue;
    }

    var datasets = [
        {
            label: data.name,
            data: data.values,
            borderColor: chartColors.blue,
            backgroundColor: gradient,
            borderWidth: 2.5,
            pointRadius: 5,
            pointBackgroundColor: pointColors,
            pointBorderColor: pointBorderColors,
            pointBorderWidth: 2,
            pointHoverRadius: 7,
            fill: true,
            tension: 0.4,
        },
    ];

    // Reference range as shaded band
    if (data.ref_min && data.ref_max &&
        data.ref_min.some(function(v) { return v !== null; }) &&
        data.ref_max.some(function(v) { return v !== null; })) {

        datasets.push({
            label: 'Ref. M\u00e1x.',
            data: data.ref_max,
            borderColor: chartColors.refLine,
            borderWidth: 1,
            borderDash: [4, 4],
            pointRadius: 0,
            fill: '+1',
            backgroundColor: chartColors.refBandBg,
        });
        datasets.push({
            label: 'Ref. M\u00edn.',
            data: data.ref_min,
            borderColor: chartColors.refLine,
            borderWidth: 1,
            borderDash: [4, 4],
            pointRadius: 0,
            fill: false,
        });
    } else {
        if (data.ref_min && data.ref_min.some(function(v) { return v !== null; })) {
            datasets.push({
                label: 'M\u00edn.',
                data: data.ref_min,
                borderColor: 'rgba(16, 185, 129, 0.4)',
                borderWidth: 1,
                borderDash: [5, 5],
                pointRadius: 0,
                fill: false,
            });
        }
        if (data.ref_max && data.ref_max.some(function(v) { return v !== null; })) {
            datasets.push({
                label: 'M\u00e1x.',
                data: data.ref_max,
                borderColor: 'rgba(239, 68, 68, 0.4)',
                borderWidth: 1,
                borderDash: [5, 5],
                pointRadius: 0,
                fill: false,
            });
        }
    }

    var labels = data.dates.map(function(d) {
        var parts = d.split('-');
        return parts[2] + '/' + parts[1] + '/' + parts[0].slice(2);
    });

    new Chart(canvas, {
        type: 'line',
        data: { labels: labels, datasets: datasets },
        options: Object.assign({}, chartDefaults, {
            plugins: Object.assign({}, chartDefaults.plugins, {
                legend: { display: false },
                filler: { propagate: true },
            }),
        }),
    });
}


/* ===== Radar Chart - Health by Category ===== */

function renderRadarChart(canvasId, categoryData) {
    _categoryHealthData = categoryData;
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;

    var labels = [];
    var values = [];
    var cats = Object.keys(categoryData);

    cats.forEach(function(cat) {
        labels.push(cat);
        values.push(categoryData[cat].pct_normal);
    });

    var ctx = canvas.getContext('2d');

    new Chart(canvas, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Sa\u00fade (%)',
                data: values,
                backgroundColor: 'rgba(59, 130, 246, 0.2)',
                borderColor: chartColors.blue,
                borderWidth: 2.5,
                pointBackgroundColor: function(context) {
                    var val = context.raw;
                    if (val >= 90) return chartColors.green;
                    if (val >= 60) return chartColors.yellow;
                    return chartColors.red;
                },
                pointBorderColor: chartColors.pointBorder,
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: chartColors.tooltipBg,
                    titleColor: chartColors.tooltipTitle,
                    bodyColor: chartColors.tooltipBody,
                    borderColor: chartColors.blue,
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 10,
                    callbacks: {
                        label: function(ctx) {
                            return ctx.raw + '% normal';
                        },
                    },
                },
            },
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        stepSize: 25,
                        color: chartColors.text,
                        backdropColor: 'transparent',
                        font: { size: 10 },
                    },
                    grid: { color: chartColors.grid },
                    angleLines: { color: chartColors.grid },
                    pointLabels: {
                        color: chartColors.white,
                        font: { size: 12, weight: '500' },
                    },
                },
            },
        },
    });
}


/* ===== Donut Chart - Normal vs Abnormal ===== */

function renderDonutChart(canvasId, normalCount, abnormalCount) {
    _normalCountData = normalCount;
    _abnormalCountData = abnormalCount;
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;

    var total = normalCount + abnormalCount;

    new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: ['Normal', 'Alterado'],
            datasets: [{
                data: [normalCount, abnormalCount],
                backgroundColor: [
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(245, 158, 11, 0.8)',
                ],
                borderColor: [
                    'rgba(16, 185, 129, 1)',
                    'rgba(245, 158, 11, 1)',
                ],
                borderWidth: 2,
                hoverOffset: 8,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '68%',
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        color: chartColors.text,
                        padding: 16,
                        usePointStyle: true,
                        pointStyle: 'circle',
                        font: { size: 12 },
                    },
                },
                tooltip: {
                    backgroundColor: 'rgba(26, 26, 36, 0.95)',
                    titleColor: '#e8e8ed',
                    bodyColor: '#a0a0b0',
                    borderColor: '#3b82f6',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 10,
                    callbacks: {
                        label: function(ctx) {
                            var pct = Math.round(ctx.raw / total * 100);
                            return ctx.label + ': ' + ctx.raw + ' (' + pct + '%)';
                        },
                    },
                },
            },
        },
        plugins: [{
            id: 'donutCenterText',
            afterDraw: function(chart) {
                var ctx = chart.ctx;
                var centerX = (chart.chartArea.left + chart.chartArea.right) / 2;
                var centerY = (chart.chartArea.top + chart.chartArea.bottom) / 2;

                ctx.save();
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';

                ctx.font = 'bold 28px -apple-system, BlinkMacSystemFont, sans-serif';
                ctx.fillStyle = chartColors.white;
                ctx.fillText(total, centerX, centerY - 8);

                ctx.font = '12px -apple-system, BlinkMacSystemFont, sans-serif';
                ctx.fillStyle = chartColors.text;
                ctx.fillText('biomarcadores', centerX, centerY + 14);

                ctx.restore();
            },
        }],
    });
}


/* ===== Gauge Charts - Critical Biomarkers ===== */

function renderGaugeCharts(containerId, biomarkers) {
    _criticalBiomarkersData = biomarkers;
    var container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = '';

    // Show top 6 most deviated
    var top = biomarkers.slice(0, 6);

    top.forEach(function(bm) {
        // Wrap entire gauge card in a link to the biomarker detail page
        var gaugeUrl = window.location.pathname.replace(/\/$/, '') + '/biomarker/' + bm.code + '/';
        var link = document.createElement('a');
        link.href = gaugeUrl;
        link.className = 'gauge-link';

        var gaugeCard = document.createElement('div');
        gaugeCard.className = 'gauge-card';
        gaugeCard.addEventListener('click', (function(url) {
            return function(e) { e.preventDefault(); window.location.href = url; };
        })(gaugeUrl));

        var canvasWrap = document.createElement('div');
        canvasWrap.className = 'gauge-canvas-wrap';

        var canvas = document.createElement('canvas');
        canvas.width = 180;
        canvas.height = 110;
        canvasWrap.appendChild(canvas);

        var valueDiv = document.createElement('div');
        valueDiv.className = 'gauge-value';
        valueDiv.innerHTML = '<span class="gauge-number">' + bm.value + '</span><span class="gauge-unit">' + bm.unit + '</span>';

        var nameDiv = document.createElement('div');
        nameDiv.className = 'gauge-name';
        nameDiv.textContent = bm.name;

        var deviationDiv = document.createElement('div');
        deviationDiv.className = 'gauge-deviation ' + (bm.status === 'high' ? 'gauge-deviation--high' : 'gauge-deviation--low');
        deviationDiv.textContent = (bm.status === 'high' ? '\u2191' : '\u2193') + ' ' + bm.deviation + '% ' + (bm.status === 'high' ? 'acima' : 'abaixo');

        var hintDiv = document.createElement('div');
        hintDiv.className = 'gauge-hint';
        hintDiv.textContent = 'Ver detalhes \u2192';

        gaugeCard.appendChild(canvasWrap);
        gaugeCard.appendChild(valueDiv);
        gaugeCard.appendChild(nameDiv);
        gaugeCard.appendChild(deviationDiv);
        gaugeCard.appendChild(hintDiv);
        link.appendChild(gaugeCard);
        container.appendChild(link);

        drawGauge(canvas, bm);
    });
}

function drawGauge(canvas, bm) {
    var ctx = canvas.getContext('2d');
    var w = canvas.width;
    var h = canvas.height;
    var cx = w / 2;
    var cy = h - 10;
    var radius = 70;
    var startAngle = Math.PI;
    var endAngle = 2 * Math.PI;

    // Background arc
    ctx.beginPath();
    ctx.arc(cx, cy, radius, startAngle, endAngle);
    ctx.lineWidth = 14;
    ctx.strokeStyle = chartColors.gaugeBg;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Calculate position on gauge (0-1)
    var val = bm.value;
    var min = bm.ref_min || 0;
    var max = bm.ref_max || val * 1.5;
    var range = max - min;
    var gaugeMin = min - range * 0.5;
    var gaugeMax = max + range * 0.5;
    var pct = Math.max(0, Math.min(1, (val - gaugeMin) / (gaugeMax - gaugeMin)));

    // Colored arc (gradient from green to yellow to red)
    var filledAngle = startAngle + pct * Math.PI;

    // Draw normal zone (green)
    var normalStart = startAngle + ((min - gaugeMin) / (gaugeMax - gaugeMin)) * Math.PI;
    var normalEnd = startAngle + ((max - gaugeMin) / (gaugeMax - gaugeMin)) * Math.PI;

    ctx.beginPath();
    ctx.arc(cx, cy, radius, normalStart, normalEnd);
    ctx.lineWidth = 14;
    ctx.strokeStyle = chartColors.gaugeNormal;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Value arc
    var valueColor = bm.status === 'high' ? chartColors.red : chartColors.yellow;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, startAngle, filledAngle);
    ctx.lineWidth = 14;
    ctx.strokeStyle = valueColor;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Needle dot
    var needleX = cx + radius * Math.cos(filledAngle);
    var needleY = cy + radius * Math.sin(filledAngle);
    ctx.beginPath();
    ctx.arc(needleX, needleY, 5, 0, 2 * Math.PI);
    ctx.fillStyle = chartColors.white;
    ctx.fill();
}


/* ===== Deviation Bars Chart ===== */

function renderDeviationBars(canvasId, biomarkers) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;

    var labels = [];
    var values = [];
    var colors = [];
    var borderColors = [];
    var codes = [];

    biomarkers.forEach(function(bm) {
        labels.push(bm.name);
        codes.push(bm.code);
        values.push(bm.status === 'high' ? bm.deviation : -bm.deviation);
        if (bm.status === 'high') {
            colors.push('rgba(239, 68, 68, 0.6)');
            borderColors.push(chartColors.red);
        } else {
            colors.push('rgba(245, 158, 11, 0.6)');
            borderColors.push(chartColors.yellow);
        }
    });

    var chart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Desvio %',
                data: values,
                backgroundColor: colors,
                borderColor: borderColors,
                borderWidth: 1.5,
                borderRadius: 6,
                barPercentage: 0.7,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            onClick: function(event, elements) {
                if (elements.length > 0) {
                    var idx = elements[0].index;
                    var code = codes[idx];
                    if (code) {
                        window.location.href = window.location.pathname.replace(/\/$/, '') + '/biomarker/' + code + '/';
                    }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: chartColors.tooltipBg,
                    titleColor: chartColors.tooltipTitle,
                    bodyColor: chartColors.tooltipBody,
                    borderColor: chartColors.blue,
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 10,
                    callbacks: {
                        label: function(ctx) {
                            var val = Math.abs(ctx.raw);
                            var dir = ctx.raw > 0 ? 'acima' : 'abaixo';
                            return val.toFixed(1) + '% ' + dir + ' da refer\u00eancia';
                        },
                        afterLabel: function() {
                            return 'Clique para ver detalhes';
                        },
                    },
                },
            },
            scales: {
                x: {
                    ticks: {
                        color: chartColors.text,
                        font: { size: 11 },
                        callback: function(v) { return Math.abs(v) + '%'; },
                    },
                    grid: { color: chartColors.grid },
                },
                y: {
                    ticks: { color: chartColors.white, font: { size: 12, weight: '500' } },
                    grid: { display: false },
                },
            },
        },
    });

    // Make cursor pointer on hover over bars
    canvas.addEventListener('mousemove', function(e) {
        var elements = chart.getElementsAtEventForMode(e, 'nearest', { intersect: true }, false);
        canvas.style.cursor = elements.length > 0 ? 'pointer' : 'default';
    });
}


/* ===== Stat Value Animation ===== */

function animateStatValues() {
    var statValues = document.querySelectorAll('.stat-value');
    statValues.forEach(function(el) {
        var text = el.textContent.trim();
        var num = parseInt(text);
        if (isNaN(num) || num === 0) return;
        // Only animate numbers (not dates)
        if (text.indexOf('/') !== -1) return;

        var duration = 800;
        var start = 0;
        var startTime = null;

        function step(timestamp) {
            if (!startTime) startTime = timestamp;
            var progress = Math.min((timestamp - startTime) / duration, 1);
            var eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
            el.textContent = Math.round(eased * num);
            if (progress < 1) requestAnimationFrame(step);
        }

        el.textContent = '0';
        requestAnimationFrame(step);
    });
}


/* ===== Biomarker Detail Chart ===== */

function renderBiomarkerChart(canvasId, data) {
    _biomarkerDetailData = data;
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;

    var labels = data.dates.map(function(d) {
        var parts = d.split('-');
        return parts[2] + '/' + parts[1] + '/' + parts[0];
    });

    var ctx = canvas.getContext('2d');
    var gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, chartColors.gradientTop);
    gradient.addColorStop(1, chartColors.gradientBottom);

    var datasets = [
        {
            label: data.name,
            data: data.values,
            borderColor: chartColors.blue,
            backgroundColor: gradient,
            borderWidth: 3,
            pointRadius: 6,
            pointBackgroundColor: chartColors.blue,
            pointBorderColor: chartColors.pointBorder,
            pointBorderWidth: 2,
            pointHoverRadius: 8,
            fill: true,
            tension: 0.3,
        },
    ];

    if (data.ref_min && data.ref_min.some(function(v) { return v !== null; })) {
        datasets.push({
            label: 'Refer\u00eancia M\u00edn.',
            data: data.ref_min,
            borderColor: chartColors.refLine,
            borderWidth: 2,
            borderDash: [8, 4],
            pointRadius: 0,
            fill: false,
        });
    }

    if (data.ref_max && data.ref_max.some(function(v) { return v !== null; })) {
        datasets.push({
            label: 'Refer\u00eancia M\u00e1x.',
            data: data.ref_max,
            borderColor: getTheme() === 'dark' ? 'rgba(239, 68, 68, 0.6)' : 'rgba(220, 38, 38, 0.5)',
            borderWidth: 2,
            borderDash: [8, 4],
            pointRadius: 0,
            fill: false,
        });
    }

    new Chart(canvas, {
        type: 'line',
        data: { labels: labels, datasets: datasets },
        options: Object.assign({}, chartDefaults, {
            plugins: Object.assign({}, chartDefaults.plugins, {
                legend: {
                    display: true,
                    labels: { color: chartColors.text, usePointStyle: true },
                },
                tooltip: Object.assign({}, chartDefaults.plugins.tooltip, {
                    callbacks: {
                        label: function(ctx) {
                            return ctx.dataset.label + ': ' + ctx.parsed.y + ' ' + data.unit;
                        },
                    },
                }),
            }),
        }),
    });
}


/* ===== Upload Form ===== */

function initUploadForm() {
    var dropZone = document.getElementById('dropZone');
    var fileInput = document.getElementById('fileInput');
    var filePreview = document.getElementById('filePreview');
    var fileName = document.getElementById('fileName');
    var removeBtn = document.getElementById('removeFile');
    var form = document.getElementById('uploadForm');
    var submitBtn = document.getElementById('submitBtn');
    var submitText = document.getElementById('submitText');
    var submitLoading = document.getElementById('submitLoading');
    var dropContent = dropZone ? dropZone.querySelector('.drop-zone-content') : null;

    if (!dropZone || !fileInput) return;

    // Click to upload
    dropZone.addEventListener('click', function() {
        if (!filePreview || filePreview.style.display === 'none') {
            fileInput.click();
        }
    });

    // Drag and drop
    dropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', function() {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            showFilePreview(e.dataTransfer.files[0]);
        }
    });

    // File selected
    fileInput.addEventListener('change', function() {
        if (fileInput.files.length > 0) {
            showFilePreview(fileInput.files[0]);
        }
    });

    // Remove file
    if (removeBtn) {
        removeBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            fileInput.value = '';
            filePreview.style.display = 'none';
            if (dropContent) dropContent.style.display = '';
        });
    }

    function showFilePreview(file) {
        if (fileName) fileName.textContent = file.name + ' (' + formatSize(file.size) + ')';
        if (filePreview) filePreview.style.display = '';
        if (dropContent) dropContent.style.display = 'none';
    }

    // Form submit - show loading
    if (form) {
        form.addEventListener('submit', function() {
            if (submitBtn) submitBtn.disabled = true;
            if (submitText) submitText.style.display = 'none';
            if (submitLoading) submitLoading.style.display = '';
        });
    }
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/* ===== Date Input Mask (dd/mm/aaaa) ===== */

function initDateMasks() {
    var dateInputs = document.querySelectorAll('.date-input');
    for (var i = 0; i < dateInputs.length; i++) {
        dateInputs[i].addEventListener('input', function(e) {
            var v = e.target.value.replace(/\D/g, '');
            if (v.length > 8) v = v.substring(0, 8);
            if (v.length >= 5) {
                v = v.substring(0, 2) + '/' + v.substring(2, 4) + '/' + v.substring(4);
            } else if (v.length >= 3) {
                v = v.substring(0, 2) + '/' + v.substring(2);
            }
            e.target.value = v;
        });
        dateInputs[i].addEventListener('keydown', function(e) {
            if (e.key === 'Backspace' || e.key === 'Delete' || e.key === 'Tab' ||
                e.key === 'ArrowLeft' || e.key === 'ArrowRight') return;
            var v = e.target.value.replace(/\D/g, '');
            if (v.length >= 8 && e.key >= '0' && e.key <= '9') {
                e.preventDefault();
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', initDateMasks);


/* ===== Biomarker Comparison ===== */

var _compareMode = false;
var _compareSelected = {};
var _compareChart = null;

var compareLineColors = [
    { line: 'rgba(59, 130, 246, 1)',   bg: 'rgba(59, 130, 246, 0.15)' },
    { line: 'rgba(239, 68, 68, 1)',    bg: 'rgba(239, 68, 68, 0.15)' },
    { line: 'rgba(16, 185, 129, 1)',   bg: 'rgba(16, 185, 129, 0.15)' },
    { line: 'rgba(245, 158, 11, 1)',   bg: 'rgba(245, 158, 11, 0.15)' },
    { line: 'rgba(139, 92, 246, 1)',   bg: 'rgba(139, 92, 246, 0.15)' },
    { line: 'rgba(236, 72, 153, 1)',   bg: 'rgba(236, 72, 153, 0.15)' },
    { line: 'rgba(20, 184, 166, 1)',   bg: 'rgba(20, 184, 166, 0.15)' },
    { line: 'rgba(249, 115, 22, 1)',   bg: 'rgba(249, 115, 22, 0.15)' }
];

function toggleCompareMode() {
    _compareMode = !_compareMode;
    var btn = document.getElementById('compareToggleBtn');
    var chartsGrid = document.getElementById('chartsGrid');
    var compareBar = document.getElementById('compareBar');

    if (_compareMode) {
        btn.classList.add('btn-primary');
        btn.classList.remove('btn-outline');
        btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg> Cancelar';
        chartsGrid.classList.add('compare-mode');
        addCompareCheckboxes();
        compareBar.style.display = '';
    } else {
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-outline');
        btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg> Comparar';
        chartsGrid.classList.remove('compare-mode');
        removeCompareCheckboxes();
        compareBar.style.display = 'none';
        clearCompareSelection();
    }
}

function addCompareCheckboxes() {
    var cards = document.querySelectorAll('#chartsGrid .chart-card');
    for (var i = 0; i < cards.length; i++) {
        var card = cards[i];
        var code = card.getAttribute('data-biomarker-code');
        if (!code) continue;

        card.style.position = 'relative';

        var check = document.createElement('div');
        check.className = 'chart-card-compare-check';
        check.setAttribute('data-code', code);
        check.innerHTML = '&#10003;';
        if (_compareSelected[code]) {
            check.classList.add('checked');
            card.classList.add('compare-selected');
        }
        check.addEventListener('click', (function(c, cd, chk) {
            return function(e) {
                e.stopPropagation();
                e.preventDefault();
                toggleCompareItem(c, cd, chk);
            };
        })(code, card, check));
        card.appendChild(check);
    }
}

function removeCompareCheckboxes() {
    var checks = document.querySelectorAll('.chart-card-compare-check');
    for (var i = 0; i < checks.length; i++) {
        checks[i].parentElement.removeChild(checks[i]);
    }
    var cards = document.querySelectorAll('#chartsGrid .chart-card');
    for (var j = 0; j < cards.length; j++) {
        cards[j].classList.remove('compare-selected');
    }
}

function toggleCompareItem(code, card, checkbox) {
    if (_compareSelected[code]) {
        delete _compareSelected[code];
        card.classList.remove('compare-selected');
        checkbox.classList.remove('checked');
    } else {
        _compareSelected[code] = true;
        card.classList.add('compare-selected');
        checkbox.classList.add('checked');
    }
    updateCompareBar();
}

function updateCompareBar() {
    var count = Object.keys(_compareSelected).length;
    var countEl = document.getElementById('compareBarCount');
    var btn = document.getElementById('compareBarBtn');
    countEl.textContent = count + ' selecionado' + (count !== 1 ? 's' : '');
    btn.disabled = count < 2;
}

function clearCompareSelection() {
    _compareSelected = {};
    var cards = document.querySelectorAll('#chartsGrid .chart-card');
    for (var i = 0; i < cards.length; i++) {
        cards[i].classList.remove('compare-selected');
    }
    var checks = document.querySelectorAll('.chart-card-compare-check');
    for (var j = 0; j < checks.length; j++) {
        checks[j].classList.remove('checked');
    }
    updateCompareBar();
}

function buildComparisonData(codes) {
    var dateSet = {};
    var i, j, code, bm;
    for (i = 0; i < codes.length; i++) {
        bm = _dashboardChartData[codes[i]];
        if (!bm) continue;
        for (j = 0; j < bm.dates.length; j++) {
            dateSet[bm.dates[j]] = true;
        }
    }

    var allDates = Object.keys(dateSet).sort();

    var aligned = {};
    for (i = 0; i < codes.length; i++) {
        code = codes[i];
        bm = _dashboardChartData[code];
        if (!bm) continue;

        var lookup = {};
        for (j = 0; j < bm.dates.length; j++) {
            lookup[bm.dates[j]] = j;
        }

        var values = [];
        var refMin = [];
        var refMax = [];
        for (j = 0; j < allDates.length; j++) {
            var idx = lookup[allDates[j]];
            if (idx !== undefined) {
                values.push(bm.values[idx]);
                refMin.push(bm.ref_min ? bm.ref_min[idx] : null);
                refMax.push(bm.ref_max ? bm.ref_max[idx] : null);
            } else {
                values.push(null);
                refMin.push(null);
                refMax.push(null);
            }
        }

        aligned[code] = {
            name: bm.name,
            unit: bm.unit,
            values: values,
            refMin: refMin,
            refMax: refMax
        };
    }

    return { dates: allDates, biomarkers: aligned };
}

function normalizeToRefPercent(values, refMin, refMax) {
    var result = [];
    for (var i = 0; i < values.length; i++) {
        if (values[i] === null) {
            result.push(null);
            continue;
        }
        var rmin = refMin[i];
        var rmax = refMax[i];
        if (rmin !== null && rmax !== null && rmax !== rmin) {
            // Both bounds: 0% = ref_min, 100% = ref_max
            result.push(((values[i] - rmin) / (rmax - rmin)) * 100);
        } else if (rmax !== null && rmax > 0 && rmin === null) {
            // Only upper bound (e.g. Colesterol Total, LDL, Triglicerideos)
            // 100% = at the limit, above = abnormal
            result.push((values[i] / rmax) * 100);
        } else if (rmin !== null && rmin > 0 && rmax === null) {
            // Only lower bound (e.g. HDL)
            // 100% = at the minimum, below = abnormal
            result.push((values[i] / rmin) * 100);
        } else {
            result.push(null);
        }
    }
    return result;
}

function showComparison() {
    var codes = Object.keys(_compareSelected);
    if (codes.length < 2) return;

    var data = buildComparisonData(codes);
    var useNormalized = codes.length >= 3;

    var panel = document.getElementById('comparePanel');
    panel.style.display = '';

    var html = '';
    html += '<div class="compare-panel-header">';
    html += '<h3>';
    html += '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg> ';
    html += 'Comparativo de Biomarcadores';
    if (useNormalized) {
        html += ' <span style="font-size:0.78rem;font-weight:400;color:var(--text-muted);">(% da faixa de refer\u00eancia)</span>';
    }
    html += '</h3>';
    html += '<button class="compare-panel-close" onclick="hideComparison()">&times;</button>';
    html += '</div>';

    html += '<div class="compare-panel-legend">';
    for (var i = 0; i < codes.length; i++) {
        var bm = data.biomarkers[codes[i]];
        if (!bm) continue;
        var color = compareLineColors[i % compareLineColors.length];
        html += '<div class="compare-legend-item">';
        html += '<span class="compare-legend-swatch" style="background:' + color.line + '"></span>';
        html += bm.name + ' (' + bm.unit + ')';
        html += '</div>';
    }
    html += '</div>';

    html += '<div class="compare-chart-container"><canvas id="compareChart"></canvas></div>';

    panel.innerHTML = html;
    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });

    renderComparisonChart(data, codes, useNormalized);

    // Exit compare mode
    toggleCompareMode();
}

function renderComparisonChart(data, codes, useNormalized) {
    if (_compareChart) {
        _compareChart.destroy();
        _compareChart = null;
    }

    var canvas = document.getElementById('compareChart');
    if (!canvas) return;

    var labels = data.dates.map(function(d) {
        var parts = d.split('-');
        return parts[2] + '/' + parts[1] + '/' + parts[0].slice(2);
    });

    var datasets = [];
    var yAxes = {};

    for (var i = 0; i < codes.length; i++) {
        var code = codes[i];
        var bm = data.biomarkers[code];
        if (!bm) continue;
        var color = compareLineColors[i % compareLineColors.length];

        var chartValues;
        if (useNormalized) {
            chartValues = normalizeToRefPercent(bm.values, bm.refMin, bm.refMax);
        } else {
            chartValues = bm.values;
        }

        var axisId;
        if (useNormalized) {
            axisId = 'y';
        } else if (i === 0) {
            axisId = 'y';
        } else {
            axisId = 'y' + i;
        }

        datasets.push({
            label: bm.name + ' (' + bm.unit + ')',
            data: chartValues,
            borderColor: color.line,
            backgroundColor: color.bg,
            borderWidth: 2.5,
            pointRadius: 5,
            pointBackgroundColor: color.line,
            pointBorderColor: chartColors.pointBorder,
            pointBorderWidth: 2,
            pointHoverRadius: 7,
            fill: false,
            tension: 0.3,
            spanGaps: false,
            yAxisID: axisId
        });

        if (!useNormalized && i > 0) {
            yAxes[axisId] = {
                type: 'linear',
                position: 'right',
                ticks: {
                    color: color.line,
                    font: { size: 11 }
                },
                grid: { display: false },
                title: {
                    display: true,
                    text: bm.unit,
                    color: color.line,
                    font: { size: 11 }
                }
            };
        }
    }

    var scales = {
        x: {
            ticks: { color: chartColors.text, font: { size: 11 } },
            grid: { color: chartColors.grid }
        }
    };

    if (useNormalized) {
        scales.y = {
            ticks: {
                color: chartColors.text,
                font: { size: 11 },
                callback: function(v) { return v + '%'; }
            },
            grid: { color: chartColors.grid },
            title: {
                display: true,
                text: '% da Faixa de Refer\u00eancia',
                color: chartColors.text,
                font: { size: 12 }
            }
        };
    } else {
        var firstBm = data.biomarkers[codes[0]];
        var firstColor = compareLineColors[0];
        scales.y = {
            type: 'linear',
            position: 'left',
            ticks: {
                color: firstColor.line,
                font: { size: 11 }
            },
            grid: { color: chartColors.grid },
            title: {
                display: true,
                text: firstBm.unit,
                color: firstColor.line,
                font: { size: 11 }
            }
        };
        var axisKeys = Object.keys(yAxes);
        for (var k = 0; k < axisKeys.length; k++) {
            scales[axisKeys[k]] = yAxes[axisKeys[k]];
        }
    }

    var customPlugins = [];
    if (useNormalized) {
        customPlugins.push({
            id: 'refBand',
            beforeDraw: function(chart) {
                var ctx = chart.ctx;
                var yScale = chart.scales.y;
                var xScale = chart.scales.x;
                var top = yScale.getPixelForValue(100);
                var bottom = yScale.getPixelForValue(0);
                ctx.save();
                ctx.fillStyle = 'rgba(16, 185, 129, 0.08)';
                ctx.fillRect(xScale.left, top, xScale.width, bottom - top);
                // Lines at 0% and 100%
                ctx.strokeStyle = 'rgba(16, 185, 129, 0.3)';
                ctx.lineWidth = 1;
                ctx.setLineDash([5, 5]);
                ctx.beginPath();
                ctx.moveTo(xScale.left, top);
                ctx.lineTo(xScale.right, top);
                ctx.moveTo(xScale.left, bottom);
                ctx.lineTo(xScale.right, bottom);
                ctx.stroke();
                ctx.restore();
            }
        });
    }

    _compareChart = new Chart(canvas, {
        type: 'line',
        data: { labels: labels, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        color: chartColors.text,
                        usePointStyle: true,
                        font: { size: 12 }
                    }
                },
                tooltip: {
                    backgroundColor: chartColors.tooltipBg,
                    titleColor: chartColors.tooltipTitle,
                    bodyColor: chartColors.tooltipBody,
                    borderColor: chartColors.blue,
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 10,
                    callbacks: {
                        label: function(ctx) {
                            var idx = ctx.datasetIndex;
                            var rawCode = codes[idx];
                            var rawBm = data.biomarkers[rawCode];
                            if (!rawBm) return ctx.dataset.label;
                            var rawVal = rawBm.values[ctx.dataIndex];
                            if (rawVal === null) return ctx.dataset.label + ': sem dados';
                            if (useNormalized) {
                                var pct = ctx.parsed.y;
                                return rawBm.name + ': ' + rawVal + ' ' + rawBm.unit + (pct !== null ? ' (' + pct.toFixed(0) + '%)' : '');
                            }
                            return rawBm.name + ': ' + rawVal + ' ' + rawBm.unit;
                        }
                    }
                }
            },
            scales: scales
        },
        plugins: customPlugins
    });
}

function hideComparison() {
    var panel = document.getElementById('comparePanel');
    if (panel) {
        panel.style.display = 'none';
        panel.innerHTML = '';
    }
    if (_compareChart) {
        _compareChart.destroy();
        _compareChart = null;
    }
}
