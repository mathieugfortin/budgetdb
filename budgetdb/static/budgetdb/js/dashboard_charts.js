/**
 * Generic function to initialize a CatType Bar Chart
 * @param {string} domId - The ID of the HTML element
 * @param {string} dataUrl - The Django JSON view URL (with params)
 * @param {string} redirectTemplate - A string containing the URL pattern for redirection
 */
function initCatTypeChart(domId, dataUrl, redirectTemplate) {
    const chartDom = document.getElementById(domId);
    if (!chartDom) return;

    const chart = echarts.init(chartDom);

    // Fetch Data
    $.getJSON(dataUrl, function(data) {
        if (data) {
            chart.setOption(data);
        }
    });

    // Handle Click Redirection
    chart.on('click', function(params) {
        const seriesIndex = params.seriesIndex;
        const seriesOption = chart.getOption().series[seriesIndex];

        const pk = seriesOption.pk;
        const start = seriesOption.start;
        const end = seriesOption.end;

        if (!pk || !redirectTemplate) return;

        // Replace placeholders in the template
        let url = redirectTemplate
            .replace('999', pk)
            .replace('START_DATE', start)
            .replace('END_DATE', end);

        window.location.href = url;
    });

    // Make chart responsive
    window.addEventListener('resize', function() {
        chart.resize();
    });
}