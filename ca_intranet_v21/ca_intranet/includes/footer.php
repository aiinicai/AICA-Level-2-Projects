<?php // includes/footer.php
try {
    $db = getDB();
    $v = $db->query("SELECT setting_value FROM app_settings WHERE setting_key='app_version'")->fetchColumn();
    $app_version = $v ?: '1.0';
} catch (Exception $e) {
    $app_version = '1.0';
}
?>
</div><!-- /.page-wrapper -->
<footer class="app-footer">
  <span><?= htmlspecialchars(firmName()) ?> &nbsp;|&nbsp; <?= APP_NAME ?> v<?= htmlspecialchars($app_version) ?></span>
  <span>FY: <?= currentFY() ?> &nbsp;|&nbsp; <?= date('d-M-Y, H:i') ?></span>
</footer>
<script src="<?= url('assets/js/app.js') ?>"></script>
</body>
</html>
