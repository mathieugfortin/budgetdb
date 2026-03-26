const formatter = new Intl.NumberFormat('en-CA', {
    style: 'currency',
    currency: 'CAD',
});


const tooltip_callback = (args) => {
    let mytooltip = `<strong>${args[0].axisValue}</strong><br />`;
    let subTotal = 0;
    let grandTotalValue = null;

    args.forEach(arg => {
        const val = parseFloat(arg.value);
        if (isNaN(val)) return;

        // Check if this is the Grand Total series
        if (arg.seriesName === 'GRAND TOTAL') {
            grandTotalValue = val;
        } else {
            // It's an individual account
            mytooltip += `
                <div style="display: flex; justify-content: space-between; gap: 20px;">
                    <span>${arg.marker} ${arg.seriesName}</span>
                    <span style="font-family: monospace;">${formatter.format(val)}</span>
                </div>`;
            subTotal += val;
        }
    });

    // Separator line
    mytooltip += `<hr style="margin: 5px 0; border-top: 1px solid rgba(255,255,255,0.2);" />`;

    // Show the dynamic sub-total of visible accounts
    mytooltip += `
        <div style="display: flex; justify-content: space-between; color: #aaa;">
            <span>Visible Sub-Total:</span>
            <span style="font-family: monospace;">${formatter.format(subTotal)}</span>
        </div>`;

    // Show the static Grand Total from the secondary axis
    if (grandTotalValue !== null) {
        mytooltip += `
            <div style="display: flex; justify-content: space-between; font-weight: bold; margin-top: 5px;">
                <span>GRAND TOTAL:</span>
                <span style="font-family: monospace;">${formatter.format(grandTotalValue)}</span>
            </div>`;
    }

    return mytooltip;
};

function initTimelineChart(targetId, jsonUrl) {
    const chartDom = document.getElementById(targetId);
    if (!chartDom) return;

    const getTheme = () => document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'dark' : null;
    
    let myChart = echarts.init(chartDom, getTheme());

    $.getJSON(jsonUrl, function(data) {
        const option = Object.assign({
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'axis',
                formatter: tooltip_callback,
                confine: true
            }
        }, data);
        
        myChart.setOption(option);
    });

    window.addEventListener('resize', () => myChart.resize());

    // Theme Observer per instance
    const observer = new MutationObserver(() => {
        myChart.dispose();
        myChart = echarts.init(chartDom, getTheme());
        // Instead of location.reload(), we just re-run the init
        initTimelineChart(targetId, jsonUrl); 
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-bs-theme'] });
}

// 2. AUTO-INIT (This keeps your current single-chart pages working!)
const currentScript = document.currentScript;
if (currentScript && currentScript.getAttribute('target')) {
    initTimelineChart(
        currentScript.getAttribute('target'),
        currentScript.getAttribute('jsonurl')
    );
}