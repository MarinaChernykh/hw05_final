from django.contrib.auth.models import User
from django.test import TestCase, Client

from ..models import Group, Post


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_1 = User.objects.create_user(username='Ivanov')
        cls.user_2 = User.objects.create_user(username='Petrov')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user_1,
            text='Тестовый пост',
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_author = Client()
        self.authorized_author.force_login(self.user_1)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_2)

    def test_urls_exist_at_desired_locations(self):
        """
        Для всех пользователей:
        страницы доступны по указанным адресам
        и используют корректные шаблоны."""
        url_templates = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/profile/Ivanov/': 'posts/profile.html',
            f'/posts/{self.post.pk}/': 'posts/post_detail.html',
        }
        for url, template in url_templates.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)

    def test_unexisting_page_url(self):
        """
        Для всех пользователей:
        страница /unexisting_page/ не существует.
        """
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, 404)

    def test_post_create_url_exists_at_desired_location(self):
        """
        Для авторизованного пользователя:
        страница создания поста /create/ доступна
        и используют корректный шаблон.
        """
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_post_edit_url_exists_at_desired_location(self):
        """
        Для автора публикации:
        Страница редактирования поста /posts/<post_id>/edit/
        доступна и используют корректный шаблон.
        """
        response = self.authorized_author.get(f'/posts/{self.post.pk}/edit/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_post_edit_url_redirect_non_author(self):
        """
        Страница /posts/<post_id>/edit/ перенаправит
        неавтора на posts/<post_id>/.
        """
        response = self.authorized_client.get(f'/posts/{self.post.pk}/edit/',
                                              follow=True)
        self.assertRedirects(response, f'/posts/{self.post.pk}/')

    def test_urls_redirect_anonymous_on_login(self):
        """
        Страницы создания и редактирования постов перенаправят
        анонимного пользователя на страницу логина."""
        url_redirect_to_url = {
            '/create/': '/auth/login/?next=/create/',
            f'/posts/{self.post.pk}/edit/':
                f'/auth/login/?next=/posts/{self.post.pk}/edit/',
        }
        for url, redirect in url_redirect_to_url.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url, follow=True)
                self.assertRedirects(response, redirect)

    def test_comment_create_url_redirect_authorized_client(self):
        """
        Для авторизованного пользователя:
        страница создания комментария
        перенаправляет на страницу поста.
        """
        response = (self.authorized_client.
                    get(f'/posts/{self.post.pk}/comment/'))
        self.assertRedirects(response, f'/posts/{self.post.pk}/')

    def test_comment_create_url_redirect_anonymous_on_login(self):
        """
        Для неавторизованного пользователя:
        страница создания комментария
        перенаправляет на страницу авторизации.
        """
        response = self.guest_client.get(f'/posts/{self.post.pk}/comment/')
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts/{self.post.pk}/comment/')
