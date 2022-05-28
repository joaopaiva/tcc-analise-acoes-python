var Site = function() {
    this.symbol = this.defaultSymbol;
    this.interval = "5m";
};

Site.prototype.defaultSymbol = "PETBR4.SA";

Site.prototype.Init = function() {
    // store the site context.
    var that = this;

    that.LoadStoredSymbols(true);
    jQuery("#symbol").on("click", function() {
        jQuery(this).val("");
    });

    jQuery('#modalAlertRemoveSymbol').on('show.bs.modal', function(event) {
        var button = jQuery(event.relatedTarget); // Button that triggered the modal
        var symbol = button.data('id'); // Extract info from data-* attributes
        var shortName = button.data('shortname'); // Extract info from data-* attributes
        // If necessary, you could initiate an AJAX request here (and then do the updating in a callback).
        // Update the modal's content. We'll use jQuery here, but you could use a data binding library or other methods instead.
        var modal = jQuery(this);
        modal.find('.btn-remove').attr('data-id', symbol);
        modal.find('.modal-body .symbolName').html(' ' + shortName);
    });

    jQuery('.btn-remove').on("click", function() {
        that.RemoveSymbol(jQuery(this).attr("data-id"));
        jQuery('#modalAlertRemoveSymbol').modal('hide');
    });
};

Site.prototype.LoadStoredSymbols = function(reloadChart = false) {

    // store the site context.
    var that = this;

    // pull the HTTP Request
    $.ajax({
        url: "/list",
        method: "GET",
        cache: false
    }).done(function(data) {

        var data = JSON.parse(data);
        if (Object.keys(data).length > 0) {
            var symbolList = "";

            for (var i = 0, l = Object.keys(data).length; i < l; i++) {
                symbolList += '<li>';
                symbolList += '<span class="getSymbol" onclick="site.getSymbolChart(this)" data-id="' +
                    data[i].sym + '">' + data[i].shortName + '</span>';
                symbolList += '<span data-toggle="modal" data-id="' + data[i].sym + '" data-shortname="' +
                    data[i].shortName + '" data-target="#modalAlertRemoveSymbol" class="removeItem">x</span>';
                symbolList += '</li>';
            }

            jQuery("ul.symbolList").html(symbolList);

            var context = {};

            context.shortName = data[0].shortName;
            context.symbol = data[0].sym;

            if(that.symbol === that.defaultSymbol)
                that.symbol = data[0].sym;

            // call the request to load the chart and pass the data context with it.
            if (reloadChart)
                that.LoadChart(context);
        } else {
            jQuery("#chart_container").html("");
            jQuery(".symbolListDiv").hide("");
        }
    });
}

Site.prototype.RemoveSymbol = function(symbolId) {

    // store the site context.
    var that = this;

    // pull the HTTP REquest
    $.ajax({
        url: "/remove?symbol=" + symbolId,
        method: "GET",
        cache: false
    }).done(function(data) {

        var context = {};

        context.removed = data.removed;
        context.message = data.message;

        // call the request to a message with result
        //            that.ShowMessage(context);
        that.LoadStoredSymbols(true);
    });
}

Site.prototype.GetQuote = function() {

    jQuery(".symbolListDiv .loadingChart").addClass("d-inline-block");

    // store the site context.
    var that = this;

    // pull the HTTP REquest
    $.ajax({
        url: "/get?symbol=" + that.symbol,
        method: "GET",
        cache: false
    }).done(function(data) {

        var data = JSON.parse(data);
        if (Object.keys(data).length > 0) {

            var context = {};

            context.shortName = data.shortName;
            context.symbol = data.sym;
            that.symbol = data.sym;

            // call the request to load the chart and pass the data context with it.
            that.LoadChart(context);

        }

    });
};

Site.prototype.SubmitForm = function() {
    this.symbol = $("#symbol").val();
    this.GetQuote();
}

Site.prototype.getIntervalChart = function(e) {
    this.interval = jQuery(e).attr("data-interval");
    console.log(this.interval);
    console.log(this.symbol);
    this.GetQuote();
}
Site.prototype.getSymbolChart = function(e) {
    this.symbol = jQuery(e).attr("data-id");
    console.log(this.interval);
    console.log(this.symbol);
    this.GetQuote(this.symbol);
}

Site.prototype.LoadChart = function(quote) {

    var that = this;
    $.ajax({
        //		url: "/historydb?symbol=" + that.symbol,
        url: "/indicators?symbol=" + that.symbol + "&interval=" + that.interval,
        method: "GET",
        cache: false
    }).done(function(data) {

        console.log(that.symbol);
        that.RenderChart(data, quote);
        var lastElementData = data[Object.keys(data)[Object.keys(data).length - 1]]
        that.RenderIndicators(lastElementData);

        console.log(series = that.chart.series)
        that.LoadStoredSymbols(false);
        //        console.log(simpleMovingAverageArray50);
    });
};

Site.prototype.RenderIndicators = function(data) {
    if (Object.keys(data).length > 0) {

        var indicators_tendency = [];
        var indicators = [];

        indicators_tendency["up"] = data.indicators_up
        indicators_tendency["down"] = data.indicators_down
        indicators_tendency["neutral"] = data.indicators_neutral
        indicators_tendency["recommendation"] = ""

        switch(data.indicators_recommendation){
            case "Strong Buy":
                indicators_tendency["recommendation"] = "Tendência de Alta Forte";
                break;

            case "Buy":
                indicators_tendency["recommendation"] = "Tendência de Alta";
                break;

            case "Neutral":
                indicators_tendency["recommendation"] = "Tendência Neutra";
                break;

            case "Sell":
                indicators_tendency["recommendation"] = "Tendência de Baixa";
                break;

            case "Strong Sell":
                indicators_tendency["recommendation"] = "Tendência de Baixa Forte";
                break;
        }


        var macd_indicator = [];
        macd_indicator["name"] = "Nível MACD (12, 26)";
        macd_indicator["value"] = data.macdSignal;
        macd_indicator["recommendation"] = data.macd_indicator.recommendation;
        indicators.push(macd_indicator);

        var cmo_9_indicator = [];
        cmo_9_indicator["name"] = "Oscilador de Momento de Chande (9)";
        cmo_9_indicator["value"] = data.cmo_9;
        cmo_9_indicator["recommendation"] = data.cmo_9_indicator.recommendation;
        indicators.push(cmo_9_indicator);

        var ema_10_indicator = [];
        ema_10_indicator["name"] = "Média Móvel Exponencial (10)";
        ema_10_indicator["value"] = data.ema_10;
        ema_10_indicator["recommendation"] = data.ema_10_indicator.recommendation;
        indicators.push(ema_10_indicator);

        var ema_20_indicator = [];
        ema_20_indicator["name"] = "Média Móvel Exponencial (20)";
        ema_20_indicator["value"] = data.ema_20;
        ema_20_indicator["recommendation"] = data.ema_20_indicator.recommendation;
        indicators.push(ema_20_indicator);

        var ema_50_indicator = [];
        ema_50_indicator["name"] = "Média Móvel Exponencial (50)";
        ema_50_indicator["value"] = data.ema_50;
        ema_50_indicator["recommendation"] = data.ema_50_indicator.recommendation;
        indicators.push(ema_50_indicator);

        var ema_100_indicator = [];
        ema_100_indicator["name"] = "Média Móvel Exponencial (100)";
        ema_100_indicator["value"] = data.ema_100;
        ema_100_indicator["recommendation"] = data.ema_100_indicator.recommendation;
        indicators.push(ema_100_indicator);

        var rsi_indicator = [];
        rsi_indicator["name"] = "Índice de Força Relativa (14)";
        rsi_indicator["value"] = data.rsi;
        rsi_indicator["recommendation"] = data.rsi_indicator.recommendation;
        indicators.push(rsi_indicator);

        var rsi_stoch_indicator = [];
        rsi_stoch_indicator["name"] = "IFR Estocástico";
        rsi_stoch_indicator["value"] = data.rsi_stoch;
        rsi_stoch_indicator["recommendation"] = data.rsi_stoch_indicator.recommendation;
        indicators.push(rsi_stoch_indicator);

        //        indicators.push([])
        //                    <tr>
        //                      <th scope="row">1</th>
        //                      <td>Mark</td>
        //                      <td>Otto</td>
        //                      <td class="indicator-action">@mdo</td>
        //                    </tr>
        var indicators_table = '<table class="table table-dark">';
            indicators_table += '<thead class="thead-light">';
            indicators_table += '<tr>';
            indicators_table += '<th scope="col">#</th>';
            indicators_table += '<th scope="col">Nome</th>';
            indicators_table += '<th scope="col">Valor</th>';
            indicators_table += '<th scope="col">Ação</th>';
            indicators_table += '</tr>';
            indicators_table += '</thead>';
            indicators_table += '<tbody>';

        var i_indicator = 0;
        var indicator_row = "";

        indicators.forEach(function logArrayElements(element, index, array) {
            i_indicator++;
            indicator_row = "";
            console.log(element["name"]);
            indicator_row += '<tr>';
            indicator_row += '<th scope="row">' + i_indicator + '</th>';
            indicator_row += '<th>' + element["name"] + '</th>';
            indicator_row += '<th>' + Math.round(element["value"] * 100) / 100 + '</th>';
            indicator_row += '<th class="indicator-action">' + element["recommendation"]+ '</th>';
            indicator_row += '</tr>';
            indicators_table += indicator_row;
        })
        indicators_table += '</tbody>';
        indicators_table += '</table>';

        console.log(indicators_table)
//        for (var i = 0, l = Object.keys(data).length; i < l; i++) {
//
//        }
        //        data[i].sym

        jQuery("#indicators").html(indicators_table);


        console.log(indicators)

        //        indicators.push([])
        //                    <tr>
        //                      <th scope="row">1</th>
        //                      <td>Mark</td>
        //                      <td>Otto</td>
        //                      <td class="indicator-action">@mdo</td>
        //                    </tr>

//        for (var i = 0, l = Object.keys(data).length; i < l; i++) {
//            symbolList += '<tr></tr>';
//        }
        //        data[i].sym

//        jQuery("ul.symbolList").html(symbolList);

//        var context = {};
//
//        context.shortName = data[0].shortName;
//        context.symbol = data[0].sym;
//        that.symbol = data[0].sym;

//        // call the request to load the chart and pass the data context with it.
//        if (reloadChart)
//            that.LoadChart(context);
    } else {
        jQuery("#chart_container").html("");
        jQuery(".symbolListDiv").hide("");
    }
}

Site.prototype.RenderChart = function(data, quote) {
    var priceData = [];
    var volumeData = [];

    var title = quote.shortName + " (" + quote.symbol + ")";

    jQuery("h4.currentSymbolName").text(title);
    console.log(data[0]._id.Datetime)
    // Map your data to desired format
    var closeData = data.map(o => ([o._id.Datetime, o.price]));
    var volumeData = data.map(o => ([o._id.Datetime, o.volume]));
    //        var series = data.map(o => ({x: data._id.Datetime, data: [{y: data.price}]}));
    //                       json.map(o => ({name: o.name, data: [{y: Number(o.Salary)}]}));

    //        console.log(close)

    // Close and Volume data
    //        for(var i in data.Close){
    //            var volume = data.Volume[i];
    //            var close = data.Close[i];
    //
    //            var dt = parseInt(i);
    //
    //            if(close != null){
    //                priceData.push([dt, close]);
    //            }
    //
    //            if(volume != null){
    //                volumeData.push([dt, volume])
    //            }
    //
    //        }

    console.log(volumeData);

    this.chart = Highcharts.stockChart('chart_container', {
        time: {
            timezone: 'Etc/GMT-1'
        },
        yAxis: [{
            labels: {
                align: 'left'
            },
            height: '60%',
            resize: {
                enabled: true
            }
        }, {
            labels: {
                align: 'left'
            },
            top: '60%',
            height: '20%',
            offset: 0
        }, {
            labels: {
                align: 'left'
            },
            top: '90%',
            height: '10%',
            offset: 0
        }],

        credits: {
            enabled: false
        },
        //
        //            title: {
        //                text: title
        //            },
        plotOptions: {
            series: {
                dataGrouping: {
                    enabled: false
                }
            }
        },
        series: [{
                name: quote.shortName,
                data: closeData,
                id: quote.shortName + '-price',
                tooltip: {
                    valueDecimals: 2
                }
            }, {
                yAxis: 1,
                type: 'macd',
                linkedTo: quote.shortName + '-price',
                params: {
                    shortPeriod: 12,
                    longPeriod: 26,
                    signalPeriod: 9,
                    period: 26
                }
            },
            {
                type: 'column',
                id: quote.shortName + '-volume',
                name: quote.shortName + ' Volume',
                data: volumeData,
                yAxis: 2
            }
        ],

        rangeSelector: {
            buttons: [{
                    type: 'minute',
                    count: 15,
                    text: '15m'
                }, {
                    type: 'minute',
                    count: 30,
                    text: '30m'
                }, {
                    type: 'hour',
                    count: 1,
                    text: '1h'
                },
                {
                    type: 'hour',
                    count: 3,
                    text: '3h'
                }, {
                    type: 'hour',
                    count: 6,
                    text: '6h'
                }, {
                    type: 'hour',
                    count: 12,
                    text: '1h'
                }, {
                    type: 'day',
                    count: 1,
                    text: '1d'
                }, {
                    type: 'day',
                    count: 3,
                    text: '3d'
                }, {
                    type: 'day',
                    count: 7,
                    text: '7d'
                }, {
                    type: 'all',
                    count: 1,
                    text: 'Tudo'
                }
            ],
            selected: 3,
            inputEnabled: false
        },

        responsive: {
            rules: [{
                condition: {
                    maxWidth: 800
                },
                chartOptions: {
                    rangeSelector: {
                        inputEnabled: false
                    }
                }
            }]
        }

    });

    jQuery(".symbolListDiv").show();
    jQuery(".symbolListDiv .loadingChart").removeClass('d-inline-block');
    jQuery("#navbarToggleExternalContent").collapse('hide');
};

var site = new Site();

jQuery(document).ready(() => {
    site.Init();
})