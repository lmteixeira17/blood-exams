/**
 * Blood Lab - Frontend JavaScript
 * Chart rendering, upload handling, and UI interactions.
 */

/* ===== Chart Configuration ===== */

var chartColors = {
    blue: 'rgba(59, 130, 246, 1)',
    blueBg: 'rgba(59, 130, 246, 0.1)',
    green: 'rgba(16, 185, 129, 0.4)',
    red: 'rgba(239, 68, 68, 0.4)',
    yellow: 'rgba(245, 158, 11, 1)',
    purple: 'rgba(139, 92, 246, 1)',
    text: 'rgba(160, 160, 176, 1)',
    grid: 'rgba(42, 42, 58, 0.5)',
};

var chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { display: false },
        tooltip: {
            backgroundColor: '#1a1a24',
            titleColor: '#e8e8ed',
            bodyColor: '#a0a0b0',
            borderColor: '#2a2a3a',
            borderWidth: 1,
            padding: 10,
            cornerRadius: 8,
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


/* ===== Dashboard Charts ===== */

function renderDashboardCharts(data) {
    var grid = document.getElementById('chartsGrid');
    if (!grid) return;

    grid.innerHTML = '';

    var codes = Object.keys(data);
    codes.forEach(function(code) {
        var bm = data[code];
        if (bm.dates.length < 1) return;

        var card = document.createElement('div');
        card.className = 'chart-card';

        var link = document.createElement('a');
        link.href = window.location.pathname.replace(/\/$/, '') + '/biomarker/' + code + '/';
        link.style.textDecoration = 'none';
        link.style.color = 'inherit';

        var title = document.createElement('h4');
        title.textContent = bm.name + ' (' + bm.unit + ')';
        link.appendChild(title);

        var container = document.createElement('div');
        container.className = 'chart-container';

        var canvas = document.createElement('canvas');
        container.appendChild(canvas);
        link.appendChild(container);
        card.appendChild(link);
        grid.appendChild(card);

        createSmallChart(canvas, bm);
    });
}

function createSmallChart(canvas, data) {
    var datasets = [
        {
            label: data.name,
            data: data.values,
            borderColor: chartColors.blue,
            backgroundColor: chartColors.blueBg,
            borderWidth: 2,
            pointRadius: 4,
            pointBackgroundColor: chartColors.blue,
            fill: true,
            tension: 0.3,
        },
    ];

    // Add reference range bands if available
    if (data.ref_min && data.ref_min.some(function(v) { return v !== null; })) {
        datasets.push({
            label: 'Mín.',
            data: data.ref_min,
            borderColor: chartColors.green,
            borderWidth: 1,
            borderDash: [5, 5],
            pointRadius: 0,
            fill: false,
        });
    }

    if (data.ref_max && data.ref_max.some(function(v) { return v !== null; })) {
        datasets.push({
            label: 'Máx.',
            data: data.ref_max,
            borderColor: chartColors.red,
            borderWidth: 1,
            borderDash: [5, 5],
            pointRadius: 0,
            fill: false,
        });
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
            }),
        }),
    });
}


/* ===== Biomarker Detail Chart ===== */

function renderBiomarkerChart(canvasId, data) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;

    var labels = data.dates.map(function(d) {
        var parts = d.split('-');
        return parts[2] + '/' + parts[1] + '/' + parts[0];
    });

    var datasets = [
        {
            label: data.name,
            data: data.values,
            borderColor: chartColors.blue,
            backgroundColor: chartColors.blueBg,
            borderWidth: 3,
            pointRadius: 6,
            pointBackgroundColor: chartColors.blue,
            pointBorderColor: '#1a1a24',
            pointBorderWidth: 2,
            fill: true,
            tension: 0.3,
        },
    ];

    if (data.ref_min && data.ref_min.some(function(v) { return v !== null; })) {
        datasets.push({
            label: 'Referência Mín.',
            data: data.ref_min,
            borderColor: chartColors.green,
            borderWidth: 2,
            borderDash: [8, 4],
            pointRadius: 0,
            fill: false,
        });
    }

    if (data.ref_max && data.ref_max.some(function(v) { return v !== null; })) {
        datasets.push({
            label: 'Referência Máx.',
            data: data.ref_max,
            borderColor: chartColors.red,
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
                    labels: { color: chartColors.text },
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
