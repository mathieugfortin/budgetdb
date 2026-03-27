//echarts_timeline.js
const formatter = new Intl.NumberFormat('en-CA', {
    style: 'currency',
    currency: 'CAD',
});

function generateTooltipHtml(args, isFiltered, isSmall) {
    let mytooltip = `<strong>${args[0].axisValue}</strong><br />`;
    let subTotal = 0;
    let grandTotalValue = null;
    debugger

    args.forEach(arg => {
        const val = parseFloat(arg.value);
        if (isNaN(val)) return;

        if (arg.seriesName === 'GRAND TOTAL') {
            grandTotalValue = val;
        } else {
            if (!isSmall) {
                mytooltip += `
                    <div style="display: flex; justify-content: space-between; gap: 20px;">
                        <span>${arg.marker} ${arg.seriesName}</span>
                        <span style="font-family: monospace;">${formatter.format(val)}</span>
                    </div>`;
            }
            subTotal += val;
        }
    });

    mytooltip += `<hr style="margin: 5px 0; border-top: 1px solid rgba(255,255,255,0.2);" />`;

    // Only show if the user has actually toggled something off
    if (isFiltered) {
        if (!isSmall) {
            mytooltip += `
                <div style="display: flex; justify-content: space-between; color: #0dcaf0; font-style: italic;">
                    <span>Visible Sub-Total:</span>
                    <span style="font-family: monospace;">${formatter.format(subTotal)}</span>
                </div>`;
        } else {
            mytooltip += `<div style="color:#aaa; font-size: 0.9em;">Visible: ${formatter.format(subTotal)}</div>`;
        }
    }
    //const finalDisplay = (grandTotal !== null) ? grandTotal : subTotal;
    //mytooltip += `<span style="color:#0dcaf0; font-weight:bold;">Total: ${formatter.format(finalDisplay)}</span>`;
   
    if (grandTotalValue !== null) {
        mytooltip += `
            <div style="display: flex; justify-content: space-between; font-weight: bold; margin-top: 5px;">
                <span>GRAND TOTAL:</span>
                <span style="font-family: monospace;">${formatter.format(grandTotalValue)}</span>
            </div>`;
    } else {
        // Fallback if no Grand Total series exists, show the subtotal as the main Total
        mytooltip += `
            <div style="display: flex; justify-content: space-between; font-weight: bold; margin-top: 5px; color: #0dcaf0;">
                <span>TOTAL:</span>
                <span style="font-family: monospace;">${formatter.format(subTotal)}</span>
            </div>`;
    }

    return mytooltip;
}

function initTimelineChart(targetId, jsonUrl) {
    const chartDom = document.getElementById(targetId);
    if (!chartDom) return;

    const getTheme = () => document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'dark' : null;

    let myChart = echarts.init(chartDom, getTheme());

    $.getJSON(jsonUrl, function(data) {
        const totalCount = data.custom_metadata ? data.custom_metadata.total_series_count : data.series.length;
        const option = Object.assign({
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'axis',
                formatter: function(args) {
                    const isSmall = chartDom.clientWidth < 500;
                    const isFiltered = args.length < totalCount;
                    return generateTooltipHtml(args, isFiltered,isSmall);
                },
                confine: true,
                enterable: false 
            }
        }, data);
        
        myChart.setOption(option);
    });

    window.addEventListener('resize', () => {
        myChart.resize();
    });


    // Theme Observer per instance
    const observer = new MutationObserver(() => {
        myChart.dispose();
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