// Load and render dashboard
async function initDashboard() {
    try {
        // Add cache-busting parameter to get fresh data
        const timestamp = new Date().getTime();
        const response = await fetch(`https://raw.githubusercontent.com/scerruti/cph50-control/main/data/runs.json?t=${timestamp}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const text = await response.text();
        const data = JSON.parse(text);
        const runs = data.runs || [];
        
        renderSummary(runs);
    } catch (error) {
        console.error('Dashboard error:', error);
        document.getElementById('content').innerHTML = `
            <div style="padding: 40px; text-align: center;">
                <p style="color: #e74c3c; font-size: 1.2em; margin-bottom: 10px;">⚠️ Error loading dashboard</p>
                <p style="color: #666; margin-bottom: 20px;">${error.message}</p>
                <p style="color: #999; font-size: 0.9em;">The data file may not exist yet. Run a charging session to populate data.</p>
            </div>
        `;
    }
}

function renderSummary(runs) {
    if (runs.length === 0) {
        document.getElementById('content').innerHTML = '<p>No data yet. Reports will appear after the first charging run.</p>';
        return;
    }
    
    // Calculate stats
    const total = runs.length;
    const successful = runs.filter(r => r.result === 'success').length;
    const failed = runs.filter(r => r.result === 'failure').length;
    const successRate = total > 0 ? ((successful / total) * 100).toFixed(1) : 0;
    
    // Latest run
    const latest = runs[0];
    const latestDate = new Date(latest.date).toLocaleDateString('en-US', { 
        weekday: 'short', 
        month: 'short', 
        day: 'numeric' 
    });
    
    // Earliest run (for week range)
    const earliest = runs[runs.length - 1];
    
    const html = `
        <div class="summary">
            <div class="card">
                <h3>Total Runs</h3>
                <div class="value">${total}</div>
            </div>
            <div class="card">
                <h3>Success Rate</h3>
                <div class="value success">${successRate}%</div>
                <small>${successful}/${total} successful</small>
            </div>
            <div class="card">
                <h3>Failures</h3>
                <div class="value failure">${failed}</div>
            </div>
            <div class="card">
                <h3>Latest Run</h3>
                <div class="value">${latestDate}</div>
                <small>${latest.result.toUpperCase()}</small>
            </div>
        </div>
        
        <div class="charts">
            <div class="chart-container">
                <canvas id="successChart"></canvas>
            </div>
            <div class="chart-container">
                <canvas id="reasonChart"></canvas>
            </div>
        </div>
        
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Time (PT)</th>
                        <th>Result</th>
                        <th>Start Time</th>
                        <th>Reason</th>
                    </tr>
                </thead>
                <tbody id="runsTableBody"></tbody>
            </table>
        </div>
    `;
    
    document.getElementById('content').innerHTML = html;
    
    // Render charts
    renderSuccessChart(runs);
    renderReasonChart(runs);
    renderTable(runs);
}

function renderSuccessChart(runs) {
    const successful = runs.filter(r => r.result === 'success').length;
    const failed = runs.filter(r => r.result === 'failure').length;
    
    const ctx = document.getElementById('successChart').getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Success', 'Failure'],
            datasets: [{
                data: [successful, failed],
                backgroundColor: ['#10b981', '#ef4444'],
                borderColor: '#ffffff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' },
                title: { display: true, text: 'Success Rate' }
            }
        }
    });
}

function renderReasonChart(runs) {
    const reasons = {};
    runs.forEach(r => {
        const reason = r.reason || 'Unknown';
        reasons[reason] = (reasons[reason] || 0) + 1;
    });
    
    const ctx = document.getElementById('reasonChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Object.keys(reasons),
            datasets: [{
                label: 'Count',
                data: Object.values(reasons),
                backgroundColor: '#667eea',
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                title: { display: true, text: 'Failure Reasons' }
            },
            scales: {
                x: { beginAtZero: true, max: Math.max(...Object.values(reasons)) + 1 }
            }
        }
    });
}

function renderTable(runs) {
    const tbody = document.getElementById('runsTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = runs.map(run => `
        <tr>
            <td>${run.date}</td>
            <td>${run.time_pt}</td>
            <td><span class="badge ${run.result}">${run.result.toUpperCase()}</span></td>
            <td>${run.start_time_pt}</td>
            <td>${run.reason}</td>
        </tr>
    `).join('');
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initDashboard);
