function ifNullTurnStr(turnParam) {
  if (turnParam == null || turnParam == "" || turnParam == "null" || turnParam == "NULL") {
    return "-";
  } else {
    return turnParam;
  }
}

/**
 * 【官网/基金子网站】ETF多码合一与新增ETF细分类
 * 新增Tab
 */
var tab = {
  main: function () {
    $('.js_navTabs').html('');
    $('.tab-link').html('');
    var str_nav =
      '<span data-value="0" class="active">股票ETF</span>' +
      '<span data-value="1">债券ETF</span>' +
      '<span data-value="2">跨境ETF</span>' +
      '<span data-value="3">商品ETF</span>';
    $('.js_navTabs').html(str_nav);
    var str_tab_0 =
      '<button type="button" value="01" class="btn btn-primary btn-sm">单市场股票（沪）ETF</button>' +
      '<button type="button" value="03" class="btn btn-light btn-sm">跨市场股票（沪深京）ETF</button>' +
      '<button type="button" value="08" class="btn btn-light btn-sm">跨市场股票（沪港深京）ETF</button>' +
      '<button type="button" value="09" class="btn btn-light btn-sm">单市场股票（科创板）ETF</button>' +
      '<button type="button" value="31" class="btn btn-light btn-sm">跨市场股票（含科创板）ETF</button>';
    var str_tab_1 =
      '<button type="button" value="02" class="btn btn-primary btn-sm">单市场债券（沪）ETF</button>' +
      '<button type="button" value="36" class="btn btn-light btn-sm" style="display:none">跨市场债券（银行间）ETF</button>' +
      '<button type="button" value="37" class="btn btn-light btn-sm">现金申赎类债券ETF</button>' +
      '<button type="button" value="32" class="btn btn-light btn-sm">跨市场债券（沪深）ETF</button>';
    var str_tab_2 =
      '<button type="button" value="33" class="btn btn-primary btn-sm">跨境ETF</button>' +
      '<button type="button" value="34" class="btn btn-light btn-sm" style="display:none">多市场跨境ETF（日内回转）</button>' +
      '<button type="button" value="35" class="btn btn-light btn-sm" style="display:none">多市场跨境ETF（非日内回转）</button>';
    var str_tab_3 =
      '<button type="button" value="38" class="btn btn-primary btn-sm" style="display:none">商品期货ETF</button>' +
      '<button type="button" value="06" class="btn btn-primary btn-sm">黄金ETF</button>';
    $(".tab_main .tab_content:eq(0) .table-responsive").before("<div class='tab-link'></div>");
    $(".tab_main .tab_content:eq(1) .table-responsive").before("<div class='tab-link'></div>");
    $(".tab_main .tab_content:eq(2) .table-responsive").before("<div class='tab-link'></div>");
    $(".tab_main .tab_content:eq(3) .table-responsive").before("<div class='tab-link'></div>");
    $(".tab_main .tab_content:eq(0) .tab-link").html(str_tab_0);
    $('.tab-link button').on("click", function (e) {
      $('button').attr("class", "btn btn-light btn-sm");
      $(this).addClass("btn-primary");
      $(this).removeClass("btn-light");
      etfList.etfListParams.ETF_CLASS = $(this).val();
      etfList.getETFList(1);
    })
    /** tab切换 */
    $.each($(".js_navTabs"), function (k, v) {
      $(this).children().eq(0).addClass("active");
      $(v).on("click", "span", function () {
        var contentIndex = $(this).index();
        if (contentIndex == 0) {
          $(".tab_main .tab_content:eq(0) .tab-link").html(str_tab_0);
          etfList.etfListParams.ETF_CLASS = '01';
          etfList.getETFList(1);
        } else if (contentIndex == 1) {
          $(".tab_main .tab_content:eq(1) .tab-link").html(str_tab_1);
          etfList.etfListParams.ETF_CLASS = '02';
          etfList.getETFList(1);
        } else if (contentIndex == 2) {
          $(".tab_main .tab_content:eq(2) .tab-link").html(str_tab_2);
          etfList.etfListParams.ETF_CLASS = '33';
          etfList.getETFList(1);
        } else if (contentIndex == 3) {
          $(".tab_main .tab_content:eq(3) .tab-link").html(str_tab_3);
          etfList.etfListParams.ETF_CLASS = '06';
          etfList.getETFList(1);
        }
        $('.tab-link button').on("click", function (e) {
          var v = $(e.target);//获取当前点击事件的元素
          $('button').attr("class", "btn btn-light btn-sm");
          $(this).addClass("btn-primary");
          $(this).removeClass("btn-light");
          etfList.etfListParams.ETF_CLASS = $(this).val();
          etfList.getETFList(1);
        })
      })
    })
  },
}


/**
 * 最新基金公告
 */
var fundAnnouncement = {
  nowDate: get_systemDate_global(),
  fundAnnouncementUrl: sseQueryURL + 'commonQuery.do',
  fundAnnouncementParams: {
    'isPagination': true,
    'pageHelp.pageSize': 25,
    'pageHelp.pageNo': 1,
    'pageHelp.beginPage': 1,
    'pageHelp.cacheSize': 1,
    'pageHelp.endPage': 1,
    'type': 'inParams',
    'sqlId': 'COMMON_PL_JJXX_JJGG_NEW_L',
    'TITLE': '', //关键字
    'SECURITY_CODE': '', //证券代码
    'BULLETIN_TYPE': '',
    'START_DATE': '',
    'END_DATE': '',
    'DATE_DESC': 1,
    'DATE_ASC': '',
    'CODE_DESC': '',
    'CODE_ASC': '',
  },
  //公告类型数据
  announcementTypeOption: [{
    value: 'reits01,fund01,reits02,fund02,reits03,fund03,reits04,fund04,reits05,fund05,reits06,fund06',
    name: '全部'
  },
  {
    value: 'reits01,fund01',
    name: '募集'
  },
  {
    value: 'reits02,fund02',
    name: '上市'
  },
  {
    value: 'reits03,fund03',
    name: '定期报告'
  },
  {
    value: 'reits04,fund04',
    name: '临时报告'
  },
  {
    value: 'reits05,fund05',
    name: '基金运作'
  },
  {
    value: 'reits06,fund06',
    name: '基金管理人公告'
  },
  ],
  init: function () {
    this.loadEvents();
    this.getStaticList();
  },
  loadEvents: function () {
    var _this = this;
    $(".js_keywords input").attr("placeholder", "关键字");
    //日期范围渲染
    laydate({
      elem: ".js_dateRange input",
      theme: '#b50005',
      format: 'yyyy-MM-dd',
      range: true,
      value: dateMaxLimit(1),
      isInitValue: false,
      min: '1990-12-19',
      trigger: 'click',
      btns: ['confirm'],
      extrabtns: [
        {
          id: "today",
          text: "今日",
          range: latestType('today')
        },
        {
          id: "tomorrow",
          text: "明日",
          range: latestType('tomorrow')
        },
        {
          id: "latestThree",
          text: "近三日",
          range: latestType('threeDay')
        },
        {
          id: "latestWeek",
          text: "近一周",
          range: latestType('week')
        },
        {
          id: "latestMonth",
          text: "近一月",
          range: latestType('monthOne')
        },
        {
          id: "latestThreeMonth",
          text: "近三月",
          range: latestType('monthThree')
        },
      ],
      done: function (value, date, endDate) {
        //选择时间触发查询
        setTimeout(function () {
          _this.setFundAnnouncementParams();
        }, 500);
      },
    });
    //下拉框数据渲染
    bootstrapSelect({
      method: function () {
        //公告类型数据渲染
        $(".js_announcementType .selectpicker").html(addSelectOption(_this.announcementTypeOption)).selectpicker('refresh').selectpicker('render');
        //下拉框改变触发查询
        $(".js_announcementType .selectpicker").on('changed.bs.select', function (e) {
          _this.setFundAnnouncementParams();
        });
      }
    });
    //点击搜索、回车触发查询
    triggerSearch(_this.setFundAnnouncementParams);
  },
  //获取静态数据
  getStaticList: function () {
    var _this = this;
    if ($('#jsonDom').length == 0) {
      $('.js_fundAnnouncement').append('<ul class="list-group list-group-flush" id="jsonDom"></ul>');
    }
    $.getJSON('/disclosure/fund/announcement/json/fund_bulletin_publish_order.json?v=' + Math.random(), function (dataJson) {
      if (dataJson.publishData && dataJson.publishData.length > 0) {
        var fundAnnouncementHtml = '';
        $.each(dataJson.publishData, function (k, v) {
          fundAnnouncementHtml += '<li class="list-group-item">';
          fundAnnouncementHtml += '<div class="codeTitle">';
          fundAnnouncementHtml += '<span class="companyCode">' + ((v.securityCode && v.securityCode != '') ? ('[' + v.securityCode + ']') : '') + '</span>';
          fundAnnouncementHtml += '<a href="' + v.bulletinUrl + '" target="_blank"><span onclick="clickFundPdf($(this))">' + v.bulletinTitle + '</span></a>';
          fundAnnouncementHtml += '</div>';
          fundAnnouncementHtml += '<span class="new_date">' + (v.discloseDate ? v.discloseDate : '-') + '</span>';
          fundAnnouncementHtml += '</li>';
        })
        $(".js_fundAnnouncement .list-group").html(fundAnnouncementHtml);
      } else {
        $(".js_fundAnnouncement .list-group").html('<li class="list-group-item">暂无数据</li>');
      }
    })
  },
  setFundAnnouncementParams: function () {
    var _this = fundAnnouncement;
    var inputCode = $("#inputCode").val(); //证券代码
    var beginDate = $(".js_dateRange input").val().substr(0, 10); //开始日期
    var endDate = $(".js_dateRange input").val().substr(-10); //结束日期
    var keywords = $(".js_keywords input").val(); //关键字
    var announceType = $(".js_announcementType .selectpicker").val(); //公告类型
    var param1 = '',
      param2 = '';
    if (announceType.substring(0, 6) == 'other-') {
      param1 = announceType.replace('other-', '');
    } else {
      param2 = announceType;
    }
    if (new Date(beginDate) > new Date(endDate)) {
      bootstrapModal({ text: "开始日期不能大于结束日期" });
      return;
    }
    //无代码，无关键字，无日期
    if (inputCode == '' && beginDate == '' && keywords == '') {
      bootstrapModal({ text: "请您指定证券代码或日期后再进行查询" });
      //代码、关键词为不空，时间为空
    } else if ((inputCode != '' || keywords != '') && beginDate == '') {
      if (isNaN(inputCode) && inputCode != '') {
        bootstrapModal({ text: "证券代码必须为6位数字，请根据智能提示选择证券代码后查询" });
      } else if (inputCode.length != 6 && inputCode != "") {
        bootstrapModal({ text: "证券代码必须为6位数字" });
      } else {
        //取第二天日期
        endDate = changeFormatDate(_this.nowDate, 1, 0, 0);
        //向前推三年
        beginDate = changeFormatDate(endDate, 0, 0, -3);
        //日期框赋值
        $(".js_dateRange input").val(beginDate + ' - ' + endDate);
        //修改参数
        _this.changeParams(inputCode, keywords, param2, param1, beginDate, endDate);
        //调用接口
        _this.getfundAnnouncementList(1);
      }
    } else if (inputCode == '' && keywords == '' && beginDate != '') {
      if (!IsDayLimit(beginDate, endDate, 0, 3, 0)) {
        bootstrapModal({ text: "您未指定证券代码，查询将只提供日期间隔不超过3个月的公告" });
        //向前推三个月
        beginDate = changeFormatDate(endDate, 0, -3, 0);
        //取当前系统时间
        //时间控件赋值
        $(".js_dateRange input").val(beginDate + ' - ' + endDate);
        _this.changeParams(inputCode, keywords, param2, param1, beginDate, endDate);
        //调用接口
        _this.getfundAnnouncementList(1);
      } else {
        //修改参数
        _this.changeParams(inputCode, keywords, param2, param1, beginDate, endDate);
        //调用接口
        _this.getfundAnnouncementList(1);
      }
      //代码或关键词不为空，时间不为空
    } else if (inputCode != '' || keywords != "" && beginDate != "") {
      if (!IsDayLimit(beginDate, endDate, 0, 0, 3)) {
        bootstrapModal({ text: "查询只提供日期间隔不超过3年的公告" });
      } else if (isNaN(inputCode) && inputCode != '') {
        bootstrapModal({ text: "证券代码必须为6位数字，请根据智能提示选择证券代码后查询" });
      } else if (inputCode.length != 6 && inputCode != "") {
        bootstrapModal({ text: "证券代码必须为6位数字" });
      } else {
        //修改参数
        _this.changeParams(inputCode, keywords, param2, param1, beginDate, endDate);
        //调用接口
        _this.getfundAnnouncementList(1);
      }
    }
  },
  changeParams: function (inputCode, keywords, param2, param1, beginDate, endDate) {
    var _this = this;
    _this.fundAnnouncementParams.SECURITY_CODE = inputCode; //证券代码
    _this.fundAnnouncementParams.TITLE = keywords; //关键字
    _this.fundAnnouncementParams.BULLETIN_TYPE = param2;
    _this.fundAnnouncementParams.OTHER_TYPE = param1;
    _this.fundAnnouncementParams.START_DATE = beginDate;
    _this.fundAnnouncementParams.END_DATE = endDate;
  },
  //排序icon的点击事件
  sortButton: function (val) {
    if (val == 1) {
      fundAnnouncement.fundAnnouncementParams.DATE_DESC = '';
      fundAnnouncement.fundAnnouncementParams.DATE_ASC = '';
      if (fundAnnouncement.fundAnnouncementParams.CODE_DESC == 1) {
        fundAnnouncement.fundAnnouncementParams.CODE_ASC = 1;
        fundAnnouncement.fundAnnouncementParams.CODE_DESC = '';
      } else {
        fundAnnouncement.fundAnnouncementParams.CODE_DESC = 1;
        fundAnnouncement.fundAnnouncementParams.CODE_ASC = '';
      }
    } else if (val == 2) {
      fundAnnouncement.fundAnnouncementParams.CODE_DESC = '';
      fundAnnouncement.fundAnnouncementParams.CODE_ASC = '';
      if (fundAnnouncement.fundAnnouncementParams.DATE_DESC == 1) {
        fundAnnouncement.fundAnnouncementParams.DATE_ASC = 1;
        fundAnnouncement.fundAnnouncementParams.DATE_DESC = '';
      } else {
        fundAnnouncement.fundAnnouncementParams.DATE_DESC = 1;
        fundAnnouncement.fundAnnouncementParams.DATE_ASC = '';
      }
    }
    fundAnnouncement.getfundAnnouncementList(1);
  },
  getfundAnnouncementList: function (pageIndex) {
    if ($('#jsonDom').length > 0) {
      $('#jsonDom').remove();
    }
    var _this = this;
    if (!paginationChange(_this.fundAnnouncementParams, pageIndex)) { //触发分页改变分页参数
      return;
    }

    //gio基金公告筛选埋点
    var _sseAnnouncementType_var = "";
    if (_this.fundAnnouncementParams.BULLETIN_TYPE == "reits01,fund01,reits02,fund02,reits03,fund03,reits04,fund04,reits05,fund05,reits06,fund06") {
      _sseAnnouncementType_var = "全部";
    } else if (_this.fundAnnouncementParams.BULLETIN_TYPE == "reits01,fund01") {
      _sseAnnouncementType_var = "募集";
    } else if (_this.fundAnnouncementParams.BULLETIN_TYPE == "reits02,fund02") {
      _sseAnnouncementType_var = "上市";
    } else if (_this.fundAnnouncementParams.BULLETIN_TYPE == "reits03,fund03") {
      _sseAnnouncementType_var = "定期报告";
    } else if (_this.fundAnnouncementParams.BULLETIN_TYPE == "reits04,fund04") {
      _sseAnnouncementType_var = "临时报告";
    } else if (_this.fundAnnouncementParams.BULLETIN_TYPE == "reits05,fund05") {
      _sseAnnouncementType_var = "基金运作";
    } else if (_this.fundAnnouncementParams.BULLETIN_TYPE == "reits06,fund06") {
      _sseAnnouncementType_var = "基金管理人公告";
    }
    gdp("track", "sseFundAnnouncementClick", {
      sseSecurityCode_var: _this.fundAnnouncementParams.SECURITY_CODE,
      sseKey_var: _this.fundAnnouncementParams.TITLE,
      sseAnnouncementType_var: _sseAnnouncementType_var,
      sseStartDate_var: _this.fundAnnouncementParams.START_DATE,
      sseEndDate_var: _this.fundAnnouncementParams.END_DATE,
    });

    var empryTr = '<tr><td colspan="5">暂无数据</td></tr>';
    var fundAnnouncementHtml = '<thead><tr>';
    fundAnnouncementHtml += '<th style="min-width: 80px;" onclick="fundAnnouncement.sortButton(1)">基金代码<span class="sort-span"><em class="caret-em caret-em-down' + (fundAnnouncement.fundAnnouncementParams.CODE_ASC == 1 ? ' caret-on' : '') + '"></em><em class="caret-em caret-em-up' + (fundAnnouncement.fundAnnouncementParams.CODE_DESC == 1 ? ' caret-on' : '') + '"></em></span></th>';
    fundAnnouncementHtml += '<th>基金扩位简称</th>';
    fundAnnouncementHtml += '<th>公告标题</th>';
    fundAnnouncementHtml += '<th></th>';
    fundAnnouncementHtml += '<th style="min-width: 80px;" onclick="fundAnnouncement.sortButton(2)">公告时间<span class="sort-span"><em class="caret-em caret-em-down' + (fundAnnouncement.fundAnnouncementParams.DATE_ASC == 1 ? ' caret-on' : '') + '"></em><em class="caret-em caret-em-up' + (fundAnnouncement.fundAnnouncementParams.DATE_DESC == 1 ? ' caret-on' : '') + '"></em></span></th>';
    fundAnnouncementHtml += '</tr></thead><tbody>';
    getJSONP({
      type: 'post',
      dataType: 'jsonp',
      url: _this.fundAnnouncementUrl,
      data: _this.fundAnnouncementParams,
      successCallback: function (data) {
        if (data && data.result && data.result.length > 0) {
          $.each(data.result, function (k, v) {
            fundAnnouncementHtml += '<tr>';
            fundAnnouncementHtml += '<td class="text-nowrap">' +
              (v.SECURITY_CODE ? v.SECURITY_CODE : "") +
              "</a></td>"; //公募REITs代码
            fundAnnouncementHtml +=
              '<td class="text-nowrap">' +
              (isNull(v.FUND_EXPANSION_ABBR) ? v.FUND_EXPANSION_ABBR : "-") +
              "</a></td>"; //扩位简称	
            fundAnnouncementHtml += '<td><a class="table_titlewrap" href="' + v.URL + '" target="_blank"><span onclick="clickFundPdf($(this))">' + v.TITLE + '</span></a></td>'; //公告标题
            fundAnnouncementHtml +=
              '<td class="text-center"><a class="iconfont iconxiazai" style="cursor: pointer;color: #bc0007 !important" href="' +
              (v.URL ? v.URL : "") +
              '" title="点击下载公告文件" download="' + (v.TITLE ? v.TITLE + obtainFileType(v.URL) : "文件" + obtainFileType(v.URL)) + '"></a></td>'; //下载
            fundAnnouncementHtml += '<td class="text-nowrap">' + v.SSEDATE + '</td>'; //公告时间
          })
          fundAnnouncementHtml += '</tbody>';
          $(".js_fundAnnouncement .table").html(fundAnnouncementHtml);
          //调用分页
          Page.navigation(".js_fundAnnouncement .pagination-box", data.pageHelp.pageCount, data.pageHelp.total, data.pageHelp.pageNo, data.pageHelp.pageSize, "fundAnnouncement.getfundAnnouncementList");
        } else {
          fundAnnouncementHtml += empryTr;
          fundAnnouncementHtml += '</tbody>';
          $(".js_fundAnnouncement .table").html(fundAnnouncementHtml);
          $(".js_fundAnnouncement .pagination-box").html("");
        }
        //搜索代码添加cookie
        popularize.saveCpyIntoCookie($("#inputCode").val().trim(), $("#inputCode"), 1);
      },
      errCallback: function () {
        fundAnnouncementHtml += empryTr;
        fundAnnouncementHtml += '</tbody>';
        $(".js_fundAnnouncement .table").html(fundAnnouncementHtml);
        $(".js_fundAnnouncement .pagination-box").html("");
      }
    })
  }
}
if ($(".js_fundAnnouncement").length > 0) {
  fundAnnouncement.init();
}

//gio基金公告pdf点击事件埋点
function clickFundPdf(t) {
  gdp("track", "sseFundAnnouncementClick", {
    sseCheckPdf_var: t.text(),
  });
}
//最新基金公告end

/**
 * etf公告
 */
var etfAnnouncement = {
  todayDate: get_systemDate_global(), //当前日期
  etfAnnouncementUrl: sseQueryURL + 'commonQuery.do', //etfurl
  etfAnnouncementParams: {
    'isPagination': true,
    'sqlId': 'COMMON_SSE_PL_JJXX_ETFGG_L',
    'pageHelp.pageSize': 25,
    'pageHelp.pageNo': 1,
    'pageHelp.beginPage': 1,
    'pageHelp.cacheSize': 1,
    'pageHelp.endPage': 1,
    'SECURITY_CODE': '', //证券代码
    'BEGIN_DATE': changeFormatDate(get_systemDate_global(), 0, -3, 0), //开始日期
    'END_DATE': get_systemDate_global(), //结束日期
    'DATE_DESC': 1,
    'DATE_ASC': '',
    'CODE_DESC': '',
    'CODE_ASC': '',
  },
  init: function () {
    this.loadEvents();
    this.getETFAnnouncementList(1);
  },
  loadEvents: function () {
    var _this = this;
    //日期范围渲染
    laydate({
      elem: ".js_dateRange input",
      theme: '#b50005',
      format: 'yyyy-MM-dd',
      range: true,
      min: '1990-12-19',
      value: dateMaxLimit(1),
      trigger: 'click',
      btns: ['confirm'],
      extrabtns: [
        {
          id: "today",
          text: "今日",
          range: latestType('today')
        },
        {
          id: "tomorrow",
          text: "明日",
          range: latestType('tomorrow')
        },
        {
          id: "latestThree",
          text: "近三日",
          range: latestType('threeDay')
        },
        {
          id: "latestWeek",
          text: "近一周",
          range: latestType('week')
        },
        {
          id: "latestMonth",
          text: "近一月",
          range: latestType('monthOne')
        },
        {
          id: "latestThreeMonth",
          text: "近三月",
          range: latestType('monthThree')
        },
      ],
      done: function (value, date, endDate) {
        //选择时间触发查询
        setTimeout(function () {
          _this.setETFAnnouncementParams();
        }, 500);
      },
    });
    triggerSearch(_this.setETFAnnouncementParams); //点击搜索、回车触发查询
  },
  setETFAnnouncementParams: function () {
    var _this = etfAnnouncement;
    var inputCode = $("#inputCode").val(); //获取证券代码
    var beginDate = $(".js_dateRange input").val().substr(0, 10); //获取开始日期
    var endDate = $(".js_dateRange input").val().substr(-10); //获取结束日期
    if (inputCode == '' && beginDate == '') {
      bootstrapModal({ text: "请您指定证券代码或日期后再进行查询" });
    } else {
      if (beginDate > endDate) {
        bootstrapModal({ text: "开始时间不能大于结束时间！" });
        return;
      }
      //代码为空，时间不为空
      if (inputCode == '' && beginDate != '') {
        //如果日期相差大于30天，默认赋值所选日期向前推3个月
        if (!IsDayLimit(beginDate, endDate, 0, 3, 0)) {
          bootstrapModal({ text: '您未指定证券代码，查询将只提供日期间隔不超过3个月的公告' });
          beginDate = changeFormatDate(endDate, 0, -3, 0);
        }
        //代码日期都不为空查三年数据，所选日期超出三年，默认由所选结束日期向前推三年  
      } else if (inputCode != '' && beginDate != '') {
        if (!IsDayLimit(beginDate, endDate, 0, 0, 3)) {
          bootstrapModal({ text: "查询只提供日期间隔不超过3年的公告" });
          beginDate = changeFormatDate(endDate, 0, 0, -3);
        }
        //代码不为空，日期为空，结束日期为当前日期，开始日期向前推三个月
      } else if (inputCode != '' && beginDate == '') {
        endDate = _this.todayDate;
        beginDate = changeFormatDate(endDate, -90, 0, 0);
      }
      $(".js_dateRange input").val(beginDate + ' - ' + endDate);
      _this.etfAnnouncementParams.SECURITY_CODE = inputCode;
      _this.etfAnnouncementParams.BEGIN_DATE = beginDate;
      _this.etfAnnouncementParams.END_DATE = endDate;
      _this.getETFAnnouncementList(1);
    }
  },
  //排序icon的点击事件
  sortButton: function (val) {
    if (val == 1) {
      etfAnnouncement.etfAnnouncementParams.DATE_DESC = '';
      etfAnnouncement.etfAnnouncementParams.DATE_ASC = '';
      if (etfAnnouncement.etfAnnouncementParams.CODE_DESC == 1) {
        etfAnnouncement.etfAnnouncementParams.CODE_ASC = 1;
        etfAnnouncement.etfAnnouncementParams.CODE_DESC = '';
      } else {
        etfAnnouncement.etfAnnouncementParams.CODE_DESC = 1;
        etfAnnouncement.etfAnnouncementParams.CODE_ASC = '';
      }
    } else if (val == 2) {
      etfAnnouncement.etfAnnouncementParams.CODE_DESC = '';
      etfAnnouncement.etfAnnouncementParams.CODE_ASC = '';
      if (etfAnnouncement.etfAnnouncementParams.DATE_DESC == 1) {
        etfAnnouncement.etfAnnouncementParams.DATE_ASC = 1;
        etfAnnouncement.etfAnnouncementParams.DATE_DESC = '';
      } else {
        etfAnnouncement.etfAnnouncementParams.DATE_DESC = 1;
        etfAnnouncement.etfAnnouncementParams.DATE_ASC = '';
      }
    }
    etfAnnouncement.getETFAnnouncementList(1);
  },
  getETFAnnouncementList: function (pageIndex) {
    var _this = this;
    if (!paginationChange(_this.etfAnnouncementParams, pageIndex)) return; //触发分页改变分页参数

    //gioETF公告筛选埋点
    gdp("track", "sseETFAnnouncementClick", {
      sseSecurityCode_var: _this.etfAnnouncementParams.SECURITY_CODE,
      sseStartDate_var: _this.etfAnnouncementParams.BEGIN_DATE,
      sseEndDate_var: _this.etfAnnouncementParams.END_DATE,
    });

    var empryTr = '<tr><td colspan="5">暂无数据</td></tr>';
    var etfAnnouncementHtml = '<thead><tr>';
    etfAnnouncementHtml += '<th style="min-width: 80px;" onclick="etfAnnouncement.sortButton(1)">基金代码<span class="sort-span"><em class="caret-em caret-em-down' + (etfAnnouncement.etfAnnouncementParams.CODE_ASC == 1 ? ' caret-on' : '') + '"></em><em class="caret-em caret-em-up' + (etfAnnouncement.etfAnnouncementParams.CODE_DESC == 1 ? ' caret-on' : '') + '"></em></span></th>';
    etfAnnouncementHtml += '<th>基金扩位简称</th>';
    etfAnnouncementHtml += '<th>公告标题</th>';
    etfAnnouncementHtml += '<th></th>';
    etfAnnouncementHtml += '<th style="min-width: 80px;" onclick="etfAnnouncement.sortButton(2)">公告时间<span class="sort-span"><em class="caret-em caret-em-down' + (etfAnnouncement.etfAnnouncementParams.DATE_ASC == 1 ? ' caret-on' : '') + '"></em><em class="caret-em caret-em-up' + (etfAnnouncement.etfAnnouncementParams.DATE_DESC == 1 ? ' caret-on' : '') + '"></em></span></th>';
    etfAnnouncementHtml += '</tr></thead><tbody>';
    getJSONP({
      type: 'post',
      dataType: 'jsonp',
      url: _this.etfAnnouncementUrl,
      data: _this.etfAnnouncementParams,
      successCallback: function (data) {
        if (data && data.result && data.result.length > 0) {
          $.each(data.result, function (k, v) {
            etfAnnouncementHtml += '<tr>';
            etfAnnouncementHtml += '<td class="text-nowrap">' +
              (v.SECURITY_CODE ? v.SECURITY_CODE : "") +
              "</td>"; //公募REITs代码
            etfAnnouncementHtml +=
              '<td class="text-nowrap">' +
              (isNull(v.FUND_EXPANSION_ABBR) ? v.FUND_EXPANSION_ABBR : "-") +
              "</td>"; //扩位简称	
            etfAnnouncementHtml += '<td><a class="table_titlewrap" href="' + v.URL + '" target="_blank"><span onclick="clickETFPdf($(this))">' + v.TITLE + '</span></a></td>'; //公告标题
            etfAnnouncementHtml +=
              '<td class="text-center"><a class="iconfont iconxiazai" style="cursor: pointer;color: #bc0007 !important" href="' +
              (v.URL ? v.URL : "") +
              '" title="点击下载公告文件" download="' + (v.TITLE ? v.TITLE + obtainFileType(v.URL) : "文件" + obtainFileType(v.URL)) + '"></a></td>'; //下载
            etfAnnouncementHtml += '<td class="text-nowrap">' + v.SSEDATE + '</td>'; //公告时间
          })
          $(".js_etfAnnouncement .table").html(etfAnnouncementHtml);
          //调用分页
          Page.navigation(".js_etfAnnouncement .pagination-box", data.pageHelp.pageCount, data.pageHelp.total, data.pageHelp.pageNo, data.pageHelp.pageSize, "etfAnnouncement.getETFAnnouncementList");
        } else {
          etfAnnouncementHtml += empryTr;
          etfAnnouncementHtml += '</tbody>';
          $(".js_etfAnnouncement .table").html(etfAnnouncementHtml);
          $(".js_etfAnnouncement .pagination-box").html("");
        }
        //搜索代码添加cookie
        popularize.saveCpyIntoCookie($("#inputCode").val().trim(), $("#inputCode"), 1);
      },
      errCallback: function () {
        etfAnnouncementHtml += empryTr;
        etfAnnouncementHtml += '</tbody>';
        $(".js_etfAnnouncement .table").html(etfAnnouncementHtml);
        $(".js_etfAnnouncement .pagination-box").html("");
      }
    })
  }
}
if ($(".js_etfAnnouncement").length > 0) {
  etfAnnouncement.init();
}

//gioETF公告pdf点击事件埋点
function clickETFPdf(t) {
  gdp("track", "sseETFAnnouncementClick", {
    sseCheckPdf_var: t.text(),
  });
}
//etf公告end

/**
 * 基础设施公募REITs公告
 */
var reits = {
  sortDate: 2,//为1的时候按code排序 2为倒序 3为正序
  sortCode: 1,//为1的时候按date排序 2为倒序 3为正序
  tomorrowDate: changeFormatDate(get_systemDate_global(), 1, 0, 0), //第二天日期
  reitsUrl: sseQueryURL + 'commonSoaQuery.do',
  reitsParams: {
    'isPagination': true,
    'pageHelp.pageSize': 25,
    'pageHelp.pageNo': 1,
    'pageHelp.beginPage': 1,
    'pageHelp.cacheSize': 1,
    'pageHelp.endPage': 1,
    'sqlId': 'REITS_BULLETIN',
    'fundCode': '',
    'startDate': '',
    'endDate': '',
    'order': 'sseDate|desc,securityCode|asc,id|asc'//默认日期倒序
  },
  init: function () {
    this.loadEvents();
  },
  loadEvents: function () {
    var _this = this;
    //获取三月前日期
    var startDate = changeFormatDate(_this.tomorrowDate, 0, -3, 0);
    _this.reitsParams.startDate = startDate;
    _this.reitsParams.endDate = _this.tomorrowDate;
    _this.getReitsList(1);
    //日期范围渲染
    laydate({
      elem: ".js_dateRange input",
      theme: '#b50005',
      format: 'yyyy-MM-dd',
      range: true,
      value: dateReitsMaxLimit(1),
      min: '1990-12-19',
      trigger: 'click',
      btns: ['confirm'],
      extrabtns: [
        {
          id: "today",
          text: "今日",
          range: latestType('today')
        },
        {
          id: "tomorrow",
          text: "明日",
          range: latestType('tomorrow')
        },
        {
          id: "latestThree",
          text: "近三日",
          range: latestType('threeDay')
        },
        {
          id: "latestWeek",
          text: "近一周",
          range: latestType('week')
        },
        {
          id: "latestMonth",
          text: "近一月",
          range: latestType('monthOne')
        },
        {
          id: "latestThreeMonth",
          text: "近三月",
          range: latestType('monthThree')
        },
      ],
      done: function (value, date, endDate) {
        //选择时间触发查询
        setTimeout(function () {
          _this.setReitsParams();
        }, 500);
      },
    });
    triggerSearch(_this.setReitsParams); //点击搜索、回车触发查询
  },
  setReitsParams: function () {
    var _this = reits;
    var inputCode = $("#inputCode").val();
    var startDate = $(".js_dateRange input").val().substr(0, 10); //开始日期
    var endDate = $(".js_dateRange input").val().substr(-10); //结束日期
    if (inputCode == '' && startDate == '') {
      bootstrapModal({ text: "请您指定证券代码或日期后再进行查询" });
      //代码不为空，日期为空，取30天数据
    } else if (inputCode != '' && startDate == '') {
      if (isNaN(inputCode)) {
        bootstrapModal({ text: "证券代码必须为6位数字，请根据智能提示选择证券代码后查询" });
      } else if (inputCode.length != 6) {
        bootstrapModal({ text: "证券代码必须为6位数字" });
      } else {
        _this.reitsParams.endDate = _this.tomorrowDate; //结束日期
        _this.reitsParams.startDate = changeFormatDate(_this.tomorrowDate, -30, 0, 0); //开始日期
        _this.reitsParams.fundCode = inputCode;
        $(".js_dateRange input").val(changeFormatDate(_this.tomorrowDate, -30, 0, 0) + ' - ' + _this.tomorrowDate);
        _this.getReitsList(1);
      }
      //代码为空，日期不为空，取30天数据
    } else if (inputCode == '' && startDate != '') {
      if (startDate > endDate) {
        bootstrapModal({ text: "开始日期不能大于结束日期" });
      } else if (!IsDayLimit(startDate, endDate, 0, 3, 0)) {
        bootstrapModal({ text: "您未指定证券代码，查询将只提供日期间隔不超过3个月的公告" });
      } else {
        _this.reitsParams.fundCode = inputCode;
        _this.reitsParams.startDate = startDate;
        _this.reitsParams.endDate = endDate;
        _this.getReitsList(1);
      }
    } else if (inputCode != '' && startDate != '') {
      if (startDate > endDate) {
        bootstrapModal({ text: "开始日期不能大于结束日期" });
      } else if (isNaN(inputCode)) {
        bootstrapModal({ text: "证券代码必须为6位数字，请根据智能提示选择证券代码后查询" });
      } else if (inputCode.length != 6) {
        bootstrapModal({ text: "证券代码必须为6位数字" });
      } else {
        _this.reitsParams.fundCode = inputCode;
        _this.reitsParams.startDate = startDate;
        _this.reitsParams.endDate = endDate;
        _this.getReitsList(1);
      }
    }
  },
  //排序icon的点击事件
  sortButton: function (val) {
    if (val == 2) {
      reits.sortCode = 1;
      if (reits.sortDate == 2) {
        reits.sortDate = 3;
        reits.reitsParams.order = 'sseDate|asc,securityCode|asc,id|asc';//日期升序
      } else {
        reits.sortDate = 2;
        reits.reitsParams.order = 'sseDate|desc,securityCode|asc,id|asc';//默认日期倒序
      }
    } else if (val == 1) {
      reits.sortDate = 1;
      if (reits.sortCode == 2) {
        reits.sortCode = 3;
        reits.reitsParams.order = 'securityCode|asc,sseDate|desc,id|asc';//代码升序
      } else {
        reits.sortCode = 2;
        reits.reitsParams.order = 'securityCode|desc,sseDate|desc,id|asc';//代码降序
      }
    }
    reits.getReitsList(1);
  },
  getReitsList: function (pageIndex) {
    var _this = this;
    if (!paginationChange(_this.reitsParams, pageIndex)) return; //触发分页改变分页参数

    //gio基础设施REITs公告筛选埋点
    gdp("track", "sseReitsAnnouncementClick", {
      sseSecurityCode_var: _this.reitsParams.fundCode,
      sseStartDate_var: _this.reitsParams.startDate,
      sseEndDate_var: _this.reitsParams.endDate,
    });

    var empryTr = '<tr><td colspan="5">暂无数据</td></tr>';
    var reitsHtml = '<thead><tr>';
    reitsHtml += '<th style="min-width: 110px;"  onclick="reits.sortButton(1)">公募REITs代码<span class="sort-span"><em class="caret-em caret-em-down' + (reits.sortCode == 3 && reits.sortCode != 1 ? ' caret-on' : '') + '"></em><em class="caret-em caret-em-up' + (reits.sortCode == 2 && reits.sortCode != 1 ? ' caret-on' : '') + '"></em></span></th>';
    reitsHtml += '<th>扩位简称</th>';
    //reitsHtml += '<th>公募REITs简称</th>';
    reitsHtml += '<th>公告标题</th>';
    reitsHtml += '<th></th>';
    reitsHtml += '<th style="min-width: 80px;"  onclick="reits.sortButton(2)">披露日期<span class="sort-span"><em class="caret-em caret-em-down' + (reits.sortDate == 3 && reits.sortDate != 1 ? ' caret-on' : '') + '"></em><em class="caret-em caret-em-up' + (reits.sortDate == 2 && reits.sortDate != 1 ? ' caret-on' : '') + '"></em></span></th>';
    reitsHtml += '</tr></thead><tbody>';
    getJSONP({
      url: _this.reitsUrl,
      data: _this.reitsParams,
      successCallback: function (data) {
        if (data && data.result && data.result.length > 0) {
          $.each(data.result, function (k, v) {
            reitsHtml += '<tr>';
            reitsHtml += '<td class="text-nowrap">' +
              (v.securityCode ? v.securityCode : "") +
              "</a></td>"; //公募REITs代码
            reitsHtml +=
              '<td class="text-nowrap">' +
              (isNull(v.fundExtAbbr) ? v.fundExtAbbr : "-") +
              "</a></td>"; //扩位简称
            //reitsHtml += '<td class="text-nowrap">' + v.fundAbbr + '</td>'; //公募REITs简称	
            reitsHtml += '<td><a class="table_titlewrap" href="' + v.url + '" target="_blank"><span onclick="clickREITsPdf($(this))">' + v.title + '</span></a></td>'; //公告标题
            reitsHtml +=
              '<td class="text-center"><a class="iconfont iconxiazai" style="cursor: pointer;color: #bc0007 !important" href="' +
              (v.url ? v.url : "") +
              '" title="点击下载公告文件" download="' + (v.title ? v.title + obtainFileType(v.url) : "文件" + obtainFileType(v.url)) + '"></a></td>'; //下载
            reitsHtml += '<td class="text-nowrap">' + v.sseDate + '</td>'; //披露日期
            reitsHtml += '</tr>';
          })
          reitsHtml += '</tbody>';
          $(".js_reits .table").html(reitsHtml);
          //调用分页
          Page.navigation(".js_reits .pagination-box", data.pageHelp.pageCount, data.pageHelp.total, data.pageHelp.pageNo, data.pageHelp.pageSize, "reits.getReitsList");
        } else {
          reitsHtml += empryTr;
          reitsHtml += '</tbody>';
          $(".js_reits .table").html(reitsHtml);
          $(".js_reits .pagination-box").html("");
        }
      },
      errCallback: function () {
        reitsHtml += empryTr;
        reitsHtml += '</tbody>';
        $(".js_reits .table").html(reitsHtml);
        $(".js_reits .pagination-box").html("");
      }
    })
  }
}
if ($(".js_reits").length > 0) {
  reits.init();
}

//gio基础设施REITs公告pdf点击事件埋点
function clickREITsPdf(t) {
  gdp("track", "sseReitsAnnouncementClick", {
    sseCheckPdf_var: t.text(),
  });
}
//基础设施公募REITs公告end

/**
 * ETF公告申购赎回清单
 */
var etfList = {
  etfListUrl: sseQueryURL + 'commonQuery.do',
  //单市场etf参数
  etfListParams: {
    'isPagination': true,
    'pageHelp.pageSize': 25,
    'pageHelp.pageNo': 1,
    'pageHelp.beginPage': 1,
    'pageHelp.cacheSize': 1,
    'pageHelp.endPage': 1,
    'sqlId': 'COMMON_SSE_PL_ETFGGSGSHQD_L',
    'ETF_CLASS': '01',
    'type': 'inParams',
    'FUND_CODE': '',//基金代码
    'KEY_WORDS': ''//关键字
  },
  init: function () {
    this.loadEvents();
    tab.main();
    this.getETFList(1);
  },
  loadEvents: function () {
    //点击关键字搜索
    $(".search_btn").on("click", function (e) {
      e.stopPropagation();
      etfList.getETFList(1);
    });
    $(".js_keywords input").attr("maxlength", "15");
  },
  //接口取数据
  getETFList: function (pageIndex) {
    var _this = this;
    var inputCode = $("#inputCode").val();//证券代码
    var keywords = keywordFiltration($(".js_keywords input").val()); //关键字
    var res = /^\d{6}$/;
    if (inputCode && !res.test(inputCode)) {
      bootstrapModal({
        text: "请输入正确的证券代码"
      });
      return;
    }
    _this.etfListParams.FUND_CODE = inputCode;
    _this.etfListParams.KEY_WORDS = keywords.trim();
    if (!paginationChange(_this.etfListParams, pageIndex)) { //修改分页参数
      return;
    }
    var emptyTr = '<tr><td colspan="7">暂无数据</tr>';
    var etfListHtml = '<thead></tr>';
    etfListHtml += '<th class="codeNameWidth">基金代码</th>';
    etfListHtml += '<th>基金名称</th>';
    etfListHtml += '<th>基金管理公司名称</th>';
    etfListHtml += '<th class="text-right">基金份额净值(元)</th>';
    etfListHtml += '<th>最新公告日期</th>';
    etfListHtml += '<th>详情</th>';
    etfListHtml += '<th>下载</th>';
    etfListHtml += '</tr></thead><tbody>';
    getJSONP({
      type: 'post',
      dataType: 'jsonp',
      url: _this.etfListUrl,
      data: _this.etfListParams,
      successCallback: function (data) {
        if (data && data.result && data.result.length > 0) {
          $.each(data.result, function (k, v) {
            etfListHtml += '<tr>';
            etfListHtml += '<td class="text-nowrap">' + v.FUNDID2 + '</td>'; //交易代码
            etfListHtml += '<td><span class="table_td_lgwrap">' + v.ETF_FULLNAME + '</span></td>'; //基金名称
            etfListHtml += '<td>' + v.FUND_COMP_NAME + '</td>'; //基金管理公司名称
            etfListHtml += '<td class="text-nowrap text-right">' + v.NAV + '</td>'; //基金份额
            etfListHtml += '<td class="text-nowrap">' + v.TRADING_DAY.substring(0, 4) + '-' + v.TRADING_DAY.substring(4, 6) + '-' + v.TRADING_DAY.substring(6, 8) + '</td>'; //最新公告日期
            etfListHtml += '<td><a href="/disclosure/fund/etflist/detail.shtml?fundid=' + v.FUNDID2 + '" target="_blank"><i class="iconfont iconwenben"></a></td>'; //详情
            etfListHtml += '<td><a class="js_download-export" href="' + sseQueryURL + 'etfDownload/downloadETF2Bulletin.do?fundCode=' + v.FUNDID2 + '" target="_blank"><i class="iconfont iconxiazai"></a></td>'; //下载
          })
          etfListHtml += '</tbody>';
          $(".js_etfList .table").html('');
          var paginationDOM = ".js_etfList .pagination-box";
          $(paginationDOM).html("");
          if (etfList.etfListParams.ETF_CLASS == '01' || etfList.etfListParams.ETF_CLASS == '03' || etfList.etfListParams.ETF_CLASS == '08' || etfList.etfListParams.ETF_CLASS == '09' || etfList.etfListParams.ETF_CLASS == '31') {
            $(".js_etfList .table:eq(0)").html(etfListHtml);
            paginationDOM = ".js_etfList .pagination-box:eq(0)";
          } else if (etfList.etfListParams.ETF_CLASS == '02' || etfList.etfListParams.ETF_CLASS == '32' || etfList.etfListParams.ETF_CLASS == '36' || etfList.etfListParams.ETF_CLASS == '37') {
            $(".js_etfList .table:eq(1)").html(etfListHtml);
            paginationDOM = ".js_etfList .pagination-box:eq(1)";
          } else if (etfList.etfListParams.ETF_CLASS == '33' || etfList.etfListParams.ETF_CLASS == '34' || etfList.etfListParams.ETF_CLASS == '35') {
            $(".js_etfList .table:eq(2)").html(etfListHtml);
            paginationDOM = ".js_etfList .pagination-box:eq(2)";
          } else if (etfList.etfListParams.ETF_CLASS == '06' || etfList.etfListParams.ETF_CLASS == '38') {
            $(".js_etfList .table:eq(3)").html(etfListHtml);
            paginationDOM = ".js_etfList .pagination-box:eq(3)";
          }
          Page.navigation(paginationDOM, data.pageHelp.pageCount, data.pageHelp.total, data.pageHelp.pageNo, data.pageHelp.pageSize, "etfList.getETFList");
        } else {
          etfListHtml += emptyTr;
          etfListHtml += '</tbody>';
          $(".js_etfList .table").html(etfListHtml);
          $(".js_etfList .pagination-box").html("");
        }
      },
      errCallback: function () {
        etfListHtml += emptyTr;
        etfListHtml += '</tbody>';
        $(".js_etfList .table").html(etfListHtml);
        $(".js_etfList .pagination-box").html("");
      }
    })
  },
}
if ($(".js_etfList").length > 0) {
  etfList.init();
}
//ETF公告申购赎回清单end

/**
 * ETF公告申购赎回清单详情
 */
var etfListDetail = {
  etfListDetailUrl: sseQueryURL + 'commonQuery.do', //ETF公告申购赎回清单url
  //ETF公告申购赎回清单参数
  etfListDetailParams: {
    isPagination: false,
    FUNDID2: getWindowHref().fundid,
    sqlId: 'COMMON_SSE_CP_JJLB_ETFJJGK_GGSGSHQD_JBXX_C'
  },
  cfgParams: {
    isPagination: false,
    FUNDID2: getWindowHref().fundid,
    sqlId: 'COMMON_SSE_CP_JJLB_ETFJJGK_GGSGSHQD_COMPONENT_C'
  },
  init: function () {
    this.getSGSHQDList();
    this.scgList();
  },
  /**
   * 申赎模式字段处理
   */
  creationRedemptionEscape: function(mechanism) {
    let mechanismName = '';
    switch(mechanism) {
      case '0':
        mechanismName = '现金申赎';
        break;
      case '1':
        mechanismName = '沪市成分证券实物对价';
        break;
      case '2':
        mechanismName = '沪市、深市成分证券实物对价';
        break;
      case '3':
        mechanismName = '银行间市场债券实物对价';
        break;
      default: 
        mechanismName = '-';
    }
    return mechanismName;
  },
  /**
   * 申购赎回基本信息
   */
  getSGSHQDList: function () {
    var _this = this;
    var emptyTr = '<tr><td colspan="6">暂无数据</td></tr>';
    var sgshqdHtml = '',
      info1 = '',
      info2 = '';
    getJSONP({
      type: 'post',
      dataType: 'jsonp',
      url: _this.etfListDetailUrl,
      data: _this.etfListDetailParams,
      successCallback: function (data) {
        var downUrl = '<a  class="tableDownload js_download-export" href="' + sseQueryURL + 'etfDownload/downloadETF2Bulletin.do?fundCode=' + getWindowHref().fundid + '">下载</a>';
        $(".js_sgshqd .title_lev3").append(downUrl);
        if (data && data.result && data.result.length > 0) {
          var res = data.result[0];
          sgshqdHtml += '<tbody>';
          sgshqdHtml += '<tr><td>最新公告日期</td><td>' + res.TRADING_DAY.substring(0, 4) + '-' + res.TRADING_DAY.substring(4, 6) + '-' + res.TRADING_DAY.substring(6, 8) + '</td></tr>';
          sgshqdHtml += '<tr><td>基金名称</td><td>' + res.FUND_NAME + '</td></tr>';
          sgshqdHtml += '<tr><td>基金管理公司名称</td><td>' + res.FUND_COMP_NAME + '</td></tr>';
          sgshqdHtml += '<tr><td>基金代码</td><td>' + res.TRADE_CODE + '</td></tr>';
          sgshqdHtml += '</tbody>';
          info1 += '<tbody>';
          info1 += '<tr><td>现金差额(单位:元)</td><td>' + res.PRE_CASH_COMPONENT + '</td></tr>';
          info1 += '<tr><td>最小申购、赎回单位净值(单位：元)</td><td>' + res.NAVPERCU + '</td></tr>';
          info1 += '<tr><td>基金份额净值(单位:元)</td><td>' + res.NAV + '</td></tr>';
          info1 += '</tbody>';
          info2 += '<tbody>';
          info2 += '<tr><td>最小申购、赎回单位的预估现金部分(单位:元)</td><td>' + res.ESTIMATED_CASH_COMPONENT + '</td></tr>';
          info2 += '<tr><td>现金替代比例上限</td><td>' + res.MAX_CASH_RATIO + '</td></tr>';
          info2 += '<tr><td>当日累计可申购的基金份额上限</td><td>' + (res.CREATION_LIMIT == 0 ? '-' : res.CREATION_LIMIT) + '</td></tr>';
          info2 += '<tr><td>当日累计可赎回的基金份额上限</td><td>' + (res.REDEMPTION_LIMIT == 0 ? '-' : res.REDEMPTION_LIMIT) + '</td></tr>';
          info2 += '<tr><td>当日净申购的基金份额上限</td><td>' + (res.NET_CREATION_LIMIT == 0 ? '-' : res.NET_CREATION_LIMIT) + '</td></tr>';
          info2 += '<tr><td>当日净赎回的基金份额上限</td><td>' + (res.NET_REDEMPTION_LIMIT == 0 ? '-' : res.NET_REDEMPTION_LIMIT) + '</td></tr>';
          info2 += '<tr><td>单个证券账户当日净申购的基金份额上限</td><td>' + (res.NET_CREATION_LIMIT_PER_ACCT == 0 ? '-' : res.NET_CREATION_LIMIT_PER_ACCT)  + '</td></tr>';
          info2 += '<tr><td>单个证券账户当日净赎回的基金份额上限</td><td>' + (res.NET_REDEMPTION_LIMIT_PER_ACCT == 0 ? '-' : res.NET_REDEMPTION_LIMIT_PER_ACCT) + '</td></tr>';
          info2 += '<tr><td>单个证券账户当日累计可申购的基金份额上限</td><td>' + (res.CREATION_LIMIT_PER_ACCT == 0 ? '-' : res.CREATION_LIMIT_PER_ACCT) + '</td></tr>';
          info2 += '<tr><td>单个证券账户当日累计可赎回的基金份额上限</td><td>' + (res.REDEMPTION_LIMIT_PER_ACCT == 0 ? '-' : res.REDEMPTION_LIMIT_PER_ACCT) + '</td></tr>';
          info2 += '<tr><td>是否需要公布IOPV</td><td>' + res.PUBLISH_IOPV + '</td></tr>';
          info2 += '<tr><td>最小申购、赎回单位(单位:份)</td><td>' + res.CREATION_REDEMPTION_UNIT + '</td></tr>';
          info2 += '<tr><td>申购赎回的允许情况</td><td>' + res.CREATION_REDEMPTION + '</td></tr>';
          info2 += '<tr><td>申购赎回模式</td><td>' + _this.creationRedemptionEscape(res.CREATION_REDEMPTION_MECHANISM) + '</td></tr>';
          info2 += '</tbody>';

          beforeDate = res.PRE_TRADING_DAY.substring(0, 4) + '-' + res.PRE_TRADING_DAY.substring(4, 6) + '-' + res.PRE_TRADING_DAY.substring(6, 8) + '';
          thisDate = res.TRADING_DAY.substring(0, 4) + '-' + res.TRADING_DAY.substring(4, 6) + '-' + res.TRADING_DAY.substring(6, 8) + '';
          $(".js_sgshqd .table").html(sgshqdHtml);
          $(".js_info1 .table").html(info1);
          $(".js_info2 .table").html(info2);
          $(".js_info1 .title_lev3").html(beforeDate + '日内容信息');
          $(".js_info2 .title_lev3").html(thisDate + '日内容信息');
        } else {
          $(".js_sgshqd .table").html(emptyTr);
          $(".js_info1 .table").html(emptyTr);
          $(".js_info2 .table").html(emptyTr);
          $(".js_info1 .title_lev3").html('内容信息');
          $(".js_info2 .title_lev3").html('内容信息');
        }
      },
      errCallback: function () {
        $(".js_sgshqd .table").html(emptyTr);
        $(".js_info1 .table").html(emptyTr);
        $(".js_info2 .table").html(emptyTr);
        $(".js_info1 .title_lev3").html('内容信息');
        $(".js_info2 .title_lev3").html('内容信息');
      }
    })
  },
  /**
   * 现金替代标识字段处理
   */
  substitutionEscape: function(flag, etfVersion) {
    let substitutionName = '';
    if (etfVersion === 'XML') {
      switch (flag) {
        case '0':
          substitutionName = '禁止';
          break;
        case '1':
          substitutionName = '允许';
          break;
        case '2':
          substitutionName = '必须';
          break;
        default: 
          substitutionName = '无';
      }
    } else {
      switch (flag) {
        case '0':
          substitutionName = '禁止';
          break;
        case '1':
          substitutionName = '允许';
          break;
        case '2':
          substitutionName = '必须';
          break;
        case '3':
          substitutionName = '深市或京市退补';
          break;
        case '4':
          substitutionName = '深市或京市必须';
          break;
        case '5':
          substitutionName = '退补';
          break;
        case '6':
          substitutionName = '必须';
          break;
        case '7':
          substitutionName = '港市退补';
          break;
        case '8':
          substitutionName = '港市必须';
          break;
        default: 
          substitutionName = '无';
      }
    }
    return substitutionName;
  },
  /**
   * 挂牌市场字段处理
   */
  marketEscape: function(market) {
    let marketName = '';
    switch (market) {
      case '101':
        marketName = '上海证券交易所';
        break;
      case '102':
        marketName = '深圳证券交易所';
        break;
      case '103':
        marketName = '香港联合交易所';
        break;
      case '105':
        marketName = '外汇交易中心';
        break;
      case '106':
        marketName = '北京证券交易所';
        break;
      case '9999':
        marketName = '其他';
        break;
      default:
        marketName = '-';
    }
    return marketName;
  },
  /**
   * 成分股信息内容
   */
  scgList: function () {
    var _this = this;
    var emptyTr = '<tr><td colspan="6">暂无数据</td></tr>';
    var cfgHtml = '';
    getJSONP({
      type: 'post',
      dataType: 'jsonp',
      url: _this.etfListDetailUrl,
      data: _this.cfgParams,
      successCallback: function (data) {
        var epptyTr = '<tr><td colspan="10"></td></tr>';
        var cfgHtml = '';
        if (data && data.result && data.result.length > 0) {
          var res = data.result;
          switch (res[0].ETF_CLASS) {
            case '4':
              cfgHtml = '<thead><tr><th>证券代码</th><th>证券简称</th><th class="text-right">证券数量(份)</th><th>现金替代标志</th><th>申购现金<br/>替代溢价比例</th><th>赎回现金<br/>替代折价比例</th><th class="text-right">替代金额<br/>(单位：人民币元)</th><th>挂牌市场</th></tr></thead><tbody>';
              break;
            case '5':
              cfgHtml = '<thead><tr><th>证券代码</th><th>证券简称</th><th class="text-right">证券数量(手)</th><th>现金替代标志</th><th>申购现金<br/>替代溢价比例</th><th>赎回现金<br/>替代折价比例</th><th class="text-right">替代金额<br/>(单位：人民币元)</th><th>挂牌市场</th></tr></thead><tbody>';
              break;
            case '6':
              cfgHtml = '<thead><tr><th>证券代码</th><th>证券简称</th><th class="text-right">证券数量(克)</th><th>现金替代标志</th><th>申购现金<br/>替代溢价比例</th><th>赎回现金<br/>替代折价比例</th><th class="text-right">替代金额<br/>(单位：人民币元)</th><th>挂牌市场</th></tr></thead><tbody>';
              break;
            default:
              cfgHtml = '<thead><tr><th>证券代码</th><th>证券简称</th><th class="text-right">股票数量(股)</th><th>现金替代标志</th><th>申购现金<br/>替代溢价比例</th><th>赎回现金<br/>替代折价比例</th><th class="text-right">替代金额<br/>(单位：人民币元)</th><th>挂牌市场</th></tr></thead><tbody>';
              break;
          }
          $.each(res, function (k, v) {
            cfgHtml += '<tr>';
            cfgHtml += '<td class="codeNameWidth">' + ifNullTurnStr(v.INSTRUMENT_ID) + '</td>'; //证券代码
            cfgHtml += '<td class="codeNameWidth">' + ifNullTurnStr(v.INSTRUMENT_NAME) + '</td>'; //证券简称
            cfgHtml += '<td class="text-right">' + ifNullTurnStr(v.QUANTITY) + '</td>'; //证券数量
            cfgHtml += '<td>' + _this.substitutionEscape(v.SUBSTITUTION_FLAG, v.ETF_VERSION) + '</td>'; //现金替代标志
            cfgHtml += '<td>' + ifNullTurnStr(v.CREATION_PREMIUM_RATE) + '</td>'; //申购现金替代溢价比率
            cfgHtml += '<td>' + ifNullTurnStr(v.REDEMPTION_DISCOUNT_RATE) + '</td>'; //赎回现金替代折价比率
            cfgHtml += '<td class="text-right">' + ((v.SUBSTITUTION_CASH_AMOUNT != null) ? v.SUBSTITUTION_CASH_AMOUNT : "-") + '</td>'; //替代金额
            cfgHtml += '<td>' + _this.marketEscape(v.UNDERLYION_SECURITY_ID) + '</td>'; //挂牌市场
            cfgHtml += '</tr>';
          })
          $(".js_cfgInfo .table").html(cfgHtml);
        } else {
          $(".js_cfgInfo .table").html(emptyTr);
        }
      },
      errCallback: function () {
        $(".js_cfgInfo .table").html(emptyTr);
      }
    })
  }
}
if ($(".js_sgshqd").length > 0) {
  etfListDetail.init();
}
//ETF公告申购赎回清单详情end

/**
 * 交易型货币基金公告申购赎回清单
 */
var tcurrencyfund = {
  tcurrencyfundUrl: sseQueryURL + 'commonQuery.do',
  tcurrencyfundParams: {
    isPagination: true,
    sqlId: "COMMON_SSE_PL_ETFGGSGSHQD_L",
    ETF_CLASS: "05,07",
    type: "inParams",
    'pageHelp.pageSize': 25,
    'pageHelp.pageNo': 1,
    'pageHelp.beginPage': 1,
    'pageHelp.cacheSize': 1,
    'pageHelp.endPage': 1,
  },
  init: function () {
    this.getTcurrencyfundList(1);
  },
  //接口取数据
  getTcurrencyfundList: function (pageIndex) {
    var _this = this;
    if (!paginationChange(_this.tcurrencyfundParams, pageIndex)) { //触发分页改变分页参数
      return;
    }

    var emptyTr = '<tr><td colspan="7">暂无数据</tr>';
    var tcurrencyfundHtml = '<thead></tr>';
    tcurrencyfundHtml += '<th class="codeNameWidth">基金代码</th>';
    tcurrencyfundHtml += '<th>基金名称</th>';
    tcurrencyfundHtml += '<th>基金管理公司名称</th>';
    tcurrencyfundHtml += '<th class="text-right">基金份额净值(元)</th>';
    tcurrencyfundHtml += '<th>最新公告日期</th>';
    tcurrencyfundHtml += '<th>详情</th>';
    tcurrencyfundHtml += '<th>下载</th>';
    tcurrencyfundHtml += '</tr></thead><tbody>';
    getJSONP({
      type: 'post',
      dataType: 'jsonp',
      url: _this.tcurrencyfundUrl,
      data: _this.tcurrencyfundParams,
      successCallback: function (data) {
        if (data && data.result && data.result.length > 0) {
          $.each(data.result, function (k, v) {
            tcurrencyfundHtml += '<tr>';
            tcurrencyfundHtml += '<td class="text-nowrap align-middle">' + v.FUNDID2 + '</td>'; //交易代码(前端将基金代码取值从fundid1改为fundid2)
            tcurrencyfundHtml += '<td class="align-middle"><span class="table_td_lgwrap">' + v.ETF_FULLNAME + '</span></td>'; //基金名称
            tcurrencyfundHtml += '<td class="align-middle">' + v.FUND_COMP_NAME + '</td>'; //基金管理公司名称
            tcurrencyfundHtml += '<td class="text-right align-middle">' + v.NAV + '</td>'; //基金份额
            tcurrencyfundHtml += '<td class="text-nowrap align-middle">' + v.TRADING_DAY.substring(0, 4) + '-' + v.TRADING_DAY.substring(4, 6) + '-' + v.TRADING_DAY.substring(6, 8) + '</td>'; //最新公告日期
            tcurrencyfundHtml += '<td class="align-middle"><a href="/disclosure/fund/tcurrencyfund/indexDetail.shtml?fundid=' + v.FUNDID2 + '" target="_blank"><i class="iconfont iconwenben"></i></a></td>'; //详情
            tcurrencyfundHtml += '<td class="align-middle"><a class="js_download-export" href="' + sseQueryURL + 'etfDownload/downloadETF2Bulletin.do?fundCode=' + v.FUNDID2 + '" target="_blank"><i class="iconfont iconxiazai"></i></a></td>'; //下载
          })
          tcurrencyfundHtml += '</tbody>';
          $(".js_tcurrencyfund .table").html(tcurrencyfundHtml);
          Page.navigation(".js_tcurrencyfund .pagination-box", data.pageHelp.pageCount, data.pageHelp.total, data.pageHelp.pageNo, data.pageHelp.pageSize, 'tcurrencyfund.getTcurrencyfundList');

        } else {
          tcurrencyfundHtml += emptyTr;
          tcurrencyfundHtml += '</tbody>';
          $(".js_tcurrencyfund .table").html(tcurrencyfundHtml);
          $(".js_tcurrencyfund .pagination-box").html("");
        }
      },
      errCallback: function () {

      }
    })
  },
}
if ($(".js_tcurrencyfund").length > 0) {
  tcurrencyfund.init();
}
//交易型货币基金公告申购赎回清单end