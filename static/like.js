document.addEventListener("click", async function (event) {
    const btn = event.target.closest(".like-btn");
    if (!btn) return;

    event.preventDefault();
    const postPk = btn.dataset.post;

    btn.disabled = true;

    const resp = await fetch("/toggle_like", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ post_pk: postPk }),
    });

    const data = await resp.json();

    const icon = btn.querySelector("i");
    const count = btn.querySelector(".like-count");

    count.textContent = data.like_count;

    if (data.liked) {
        icon.classList.remove("fa-regular");
        icon.classList.add("fa-solid");
    } else {
        icon.classList.remove("fa-solid");
        icon.classList.add("fa-regular");
    }

    btn.disabled = false;
});
