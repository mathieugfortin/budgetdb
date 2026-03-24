// 1. Correctly grab attributes from the script tag itself
const currentScript = document.currentScript;
const jsonurl = currentScript.getAttribute('jsonurl');
const targetId = currentScript.getAttribute('target');
const chartDom = document.getElementById(targetId);

// 2. Initialize chart with theme detection
function getTheme() {
    return document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'dark' : null;
}

let myChart = echarts.init(chartDom, getTheme());

const formatter = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
});

let tooltip_callback = (args) => {
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

let tooltip_callback3 = (args) => {
    let mytooltip = `<strong>${args[0].axisValue}</strong><br />`;
    let total = 0;
    
    args.forEach(arg => {
        // Only sum and display if the value is a number (ECharts handles hidden series by excluding them from args)
        if (!isNaN(arg.value) && arg.value !== null) {
            mytooltip += `
                <div style="display: flex; justify-content: space-between; gap: 20px;">
                    <span>${arg.marker} ${arg.seriesName}</span>
                    <span style="font-family: monospace;">${formatter.format(arg.value)}</span>
                </div>`;
            total += parseFloat(arg.value);
        }
    });

    mytooltip += `
        <div style="border-top: 1px solid rgba(255,255,255,0.2); margin-top: 5px; padding-top: 5px; display: flex; justify-content: space-between;">
            <strong>Visible Total:</strong>
            <strong style="font-family: monospace;">${formatter.format(total)}</strong>
        </div>`;
    return mytooltip;
};

// 4. Fetch and Render
$(document).ready(function() {
    $.getJSON(jsonurl, function(data) {
        const option = Object.assign({
            backgroundColor: 'transparent', // Let Bootstrap card background show through
            tooltip: {
                trigger: 'axis',
                formatter: tooltip_callback,
                confine: true // Keeps tooltip inside the chart boundaries
            }
        }, data);
        
        myChart.setOption(option);
    });
});

// 5. Theme Switching Support
// This listens for the Bootstrap theme toggle and re-initializes the chart
const observer = new MutationObserver(() => {
    const theme = getTheme();
    // ECharts requires dispose/init to change the core theme colors
    myChart.dispose();
    myChart = echarts.init(chartDom, theme);
    // Trigger a reload of the options from the global variable or re-fetch
    location.reload(); 
    // Optimization: Store the 'option' globally to use myChart.setOption(option) 
    // here instead of a full reload if performance is an issue.
});

observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-bs-theme'] });

// 6. Optimized Resize
window.addEventListener('resize', () => {
    myChart.resize();
});