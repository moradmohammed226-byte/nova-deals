function searchDeals() {
  const input = document.getElementById("searchInput");
  const query = input.value.trim();

  if (!query) {
    alert("اكتب اسم المنتج أو العرض أولاً.");
    return;
  }

  window.location.href = "deals/index.html?search=" + encodeURIComponent(query);
}
