$(function(){

    function applyEditableModel() {


        $('.editable-model:not(.editable-bound)').each(function() {
            var me = $(this);
            var htmlMode = false;

            if (me.data('html')) {
                var editor = new MediumEditor(me, {
                    buttonLabels: 'fontawesome',
                    toolbar: {
                        buttons: ['bold', 'italic', 'underline', 'strikethrough',

                            // 'justifyCenter', 'justifyFull', 'justifyLeft', 'justifyRight',
                            'anchor', 'header2', 'header3', 'header4', 'orderedlist', 'unorderedlist', 'indent', 'outdent', 'quote', 'table',
                            'quote', 'aside'
                        ],
                        // static: true,
                        // sticky: true,
                        // updateOnEmptySelection: true
                    },
                    placeholder: {
                        text: ''
                    },
                    extensions: {
                      table: new MediumEditorTable(),

                      'quote': new MediumButton({
                          label:'<i class="fas fa-quote-right"></i>',
                          start:'<blockquote><p>',
                          end:'</p></blockquote>'
                      }),

                      'aside': new MediumButton({
                          label:'<i class="fas fa-angle-double-right"></i>',
                          start:'<aside><p>',
                          end:'</p></aside>'
                      }),
                      'header2': new MediumButton({
                          label:'H2',
                          start:'<h2>',
                          end:'</h2>'
                      }),
                      'header3': new MediumButton({
                          label:'H3',
                          start:'<h3>',
                          end:'</h3>'
                      }),
                      'header4': new MediumButton({
                          label:'H4',
                          start:'<h4>',
                          end:'</h4>'
                      }),
                    },
                    paste: {
                        cleanPastedHTML: true
                    }
                });

                //
                me.mediumInsert({
                    editor: editor,
                    addons: {
                        images: {
                            fileUploadOptions: {
                                url: '/en/api/upload_image'
                            },
                            deleteScript: '/en/api/delete_image'
                        }
                    }

                });
                htmlMode = true;

                editor.subscribe('blur', function() {
                    var data = me.data();
                    var allContents = editor.serialize();
                    var elContent = allContents["element-0"].value;
                    data['value'] = elContent;

                    $.post(data.saveUrl, {
                        editableField: data.editableField,
                        editableModel: data.editableModel,
                        editablePk: data.editablePk,
                        value: elContent
                    }, function (ret) {
                        console.log(ret);
                    });
                });

            }

            if (!htmlMode) {
                me.keypress(function (event) {
                    if (event.keyCode === 13) {
                        me.blur();
                    }
                });
            }

            me.click(function (e) {
                // prevent event from bubbling up
                e.preventDefault();
            });

            if (!htmlMode) {
                me.blur(function () {
                    var data = $(this).data();

                    $.post(data['saveUrl'], {
                        editableField: data.editableField,
                        editableModel: data.editableModel,
                        editablePk: data.editablePk,
                        value: $(this).text()
                    }, function (ret) {
                        console.log(ret);
                    });
                })
                .addClass('editable-bound');
            }
        });



    }
    applyEditableModel();

    function configureList(list) {
        applyEditableModel();

        var btn = list.find('.editable-list-btn');

        btn.click(function () {
            var data = btn.data();
            addItemInPopUp(data.editableRelatedField, data.editablePk, list);

            return false;
        });

        list.addClass('editable-list');

        var items = list.children("[data-id]:not(.editable-list-btn)");
        items.addClass('editable-item');

        $(list).sortable().bind('sortupdate', function() {
            var config = btn.data();

            config.order = $.makeArray(list.children(".editable-item").map(function(idx, item) {
                return $(item).data('id');
            })).join(',');

            $.post(config.updateSortUrl, config, function (response) {
                list.trigger('editable.modify', ['sort']);
            });
        });

        items.prepend('<div class="editable-controls">\n' +
            '                            <a href="#" class="delete"></a>\n' +
            '                            <a href="#" class="edit"></a>\n' +
            '                        </div>');

        items.find('.editable-controls .edit').click(function(e) {
            e.preventDefault();
            var el = $(this).parents('.editable-item');
            var id = el.data('id');
            if (!id) {
                console.error('Editable item does not have a data-id attribute:', el);
            } else {
                editItemInPopUp(id, list);
            }
        });
        items.find('.editable-controls .delete').click(function(e) {
            e.preventDefault();
            var el = $(this).parents('.editable-item');
            var id = el.data('id');
            if (!id) {
                console.error('Editable item does not have a data-id attribute:', el);
            } else {
                deleteInPopUp(id, list);
            }
        });

        items.find('[contenteditable]').mouseover(function() {
            list.sortable('destroy');
        }).mouseleave(function() {
            list.sortable();
        });

    }

    function reload(list) {

        list.sortable('destroy');

        var id_expr = '#' + list.attr('id');
        var loadExpr =  + ' ' + id_expr;

        $.get(location.pathname, function(data) {
            list.attr('id', null);
            list.replaceWith($(data).find(id_expr));

            configureList($(id_expr));
        });
    }

    function addItemInPopUp(parentField, parentId, list) {
        var baseUrl = list.find('.editable-list-btn').data('relatedAdminUrl');

        var href = baseUrl + 'add/?_to_field=id&_popup=1&' + parentField + '=' + parentId;

        var win = window.open(href, 'Add', 'height=500,width=800,resizable=yes,scrollbars=yes');
        win.focus();

        window.dismissAddRelatedObjectPopup = function(window, value, obj) {
            win.close();

            reload(list);
            list.trigger('editable.modify', ['add']);
        };

        return false;
    }

    function editItemInPopUp(itemId, list) {
        var baseUrl = list.find('.editable-list-btn').data('relatedAdminUrl');

        var href = baseUrl + itemId + '/change/?_to_field=id&_popup=1';
        var win = window.open(href, 'Edit', 'height=500,width=800,resizable=yes,scrollbars=yes');
        win.focus();

        window.dismissChangeRelatedObjectPopup = function(window, value, obj, new_value) {
            win.close();

            reload(list);

            list.trigger('editable.modify', ['edit']);
        };
    }



    function deleteInPopUp(itemId, list) {
        var baseUrl = list.find('.editable-list-btn').data('relatedAdminUrl');

        var href = baseUrl + itemId + '/delete/?_to_field=id&_popup=1';
        var win = window.open(href, 'Delete', 'height=500,width=800,resizable=yes,scrollbars=yes');
        win.focus();

        window.dismissDeleteRelatedObjectPopup = function(window, value) {
            win.close();

            reload(list);
            list.trigger('editable.modify', ['delete']);
        };
    }

    $('.editable-list-btn').each(function () {
        var list = $(this).parent();

        if (!list.attr('id')) {
            console.error('NB! editable list does not have id. Skipping.', list);
            return;
        }

        configureList(list);
    });

    $('[contenteditable]').parent().click(function(e) {
        e.preventDefault();
        return false;
    });


    $('.cratis-editable-trigger__btn').click(function () {
        $(this).find('img').toggleClass('on');
    });

    function openSidebar() {
        $('.cratis-editable-sidebar, .cratis-editable-wrapper, .cratis-editable-trigger').addClass('open');
        resizeIframes();
    }

    function closeSidebar() {
        $('.cratis-editable-sidebar, .cratis-editable-wrapper, .cratis-editable-trigger').removeClass('open');
    }
    $(window).resize(function() {
        resizeIframes();
    });


    var url = new URI(window.location.href);

    function resizeIframes() {
        $('.cratis-editable-sidebar__panel iframe')
            .height($('.cratis-editable-sidebar').outerHeight() - $('.cratis-editable-sidebar__panel__name').outerHeight());
    }


    $('.cratis-editable-sidebar__panel iframe').on('load', function(){
        var iframe = $(this);

        if (iframe.contents().find('#django-admin-popup-response-constants').length > 0) {
            location.reload();
        } else {
            iframe.contents().find("head")
                .append($('<link rel="stylesheet" type="text/css" href="/static/editable-model/iframe-suit-fixes.css" media="all">'));
        }
    });

    $('.cratis-editable-sidebar__panel .editable-list').on('editable.modify', function() {
        // console.log('Modify!');
        location.reload();
    });

    resizeIframes();

    $('.cratis-editable-sidebar .editable-item').on('click', function() {
            var blockId = $(this).data('id');
            var block = $('#editable-block-' + blockId);

            $([document.documentElement, document.body]).animate({
                scrollTop: $(block).offset().top
            }, 600);
        });

    $('.cratis-editable-trigger__panel-badge').click(function() {
        if ($(this).hasClass('active')) {
            $('.cratis-editable-sidebar__panel').removeClass('active');
            $('.cratis-editable-trigger__panel-badge').removeClass('active');
            closeSidebar();
            url.removeQuery('editableTab');
            history.pushState(null, null, url.href());
        } else {
            $('.cratis-editable-sidebar__panel').removeClass('active');
            $('.cratis-editable-trigger__panel-badge').removeClass('active');

            var targetId = $(this).data('target');

            $('#'+targetId).addClass('active');
            $(this).addClass('active');

            url.setQuery('editableTab', targetId);
            history.pushState(null, null, url.href());

            if (!$('.cratis-editable-sidebar').hasClass('open')) {
                openSidebar();
            }
        }
    });

    $('.cratis-editable-sidebar .closebtn').click(function() {
        $('.cratis-editable-sidebar__panel').removeClass('active');
        $('.cratis-editable-trigger__panel-badge').removeClass('active');
        closeSidebar();
        url.removeQuery('editableTab');
        history.pushState(null, null, url.href());
    });

    $('#editable-lang-selector').change(function() {
        location.href = $(this).find('option[value=' + $(this).val() + ']').data('url') + '?editableTab=editable-strings';
    });
});
