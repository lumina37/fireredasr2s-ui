$(document).ready(function () {
  [].forEach.call(document.querySelectorAll('[role="tooltip"]'), it => {
    new bootstrap.Tooltip(it);
  });

  // 拖拽上传区域
  const dropArea = $('#drop-area');
  const fileInput = $('#file-upload');
  const srtOutput = $('#srt-output');
  const downloadButton = $('#download-srt-button');










  // 拖拽事件
  dropArea.on('dragover', function (e) {
    e.preventDefault();
    dropArea.addClass('dragover');
  });

  dropArea.on('dragleave', function () {
    dropArea.removeClass('dragover');
  });

  dropArea.on('drop', function (e) {
    e.preventDefault();
    dropArea.removeClass('dragover');
    const files = e.originalEvent.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  });


  // 点击上传区域
  dropArea.on('click', function (e) {
    if (e.target !== fileInput[0]) {
      fileInput.click();
    }
  });


  fileInput.on('change', function () {
    if (fileInput[0].files.length > 0) {
      handleFile(fileInput[0].files[0]);
    }
  });

  async function handleFile(file) {
    $('#logs').text(file.name+' 识别中,用时可能较久，请耐心等待...');
	$('#zz').removeClass('d-none');
	let formData = new FormData();
    formData.append('file', file); 
    formData.append('model', $('#model').val().toUpperCase()); 

    srtOutput.val('');
    downloadButton.prop('disabled', true);
    $.ajax({
      url: '/v1/audio/transcriptions', 
      type: 'POST',
      data: formData,
	  timeout:86400000,
      processData: false,
      contentType: false,
      success: function (response) {
        srtOutput.val(response);
            downloadButton.prop('disabled', false);
			$('#logs').text('点击或拖拽音频或视频到这里，转录为SRT字幕');
			$('#zz').addClass('d-none');
      },
      error: function (err) {
        alert(err.responseJSON ? err.responseJSON['error'] : "Failed");
		$('#zz').addClass('d-none');
      }
    });


  }




  function getCurrentDateTimeString() {
    const now = new Date();

    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0'); // 月份从 0 开始，所以 + 1
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');

    return `${year}-${month}-${day}-${hours}-${minutes}-${seconds}`;
  }


  // 下载字幕
  downloadButton.on('click', function () {
    const srtText = srtOutput.val();
    if (srtText) {
      const blob = new Blob([srtText], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const link = $('<a>').attr({
        href: url,
        download: 'subtitle-' + getCurrentDateTimeString() + '.srt'
      });
      $('body').append(link);
      link[0].click();
      link.remove();
      URL.revokeObjectURL(url);
    }
  });

});