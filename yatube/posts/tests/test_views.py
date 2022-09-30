import shutil
import tempfile

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.conf import settings
from django.urls import reverse
from django import forms

from ..models import Group, Post, Comment, Follow


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Ivanov')
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.group_1 = Group.objects.create(
            title='Тестовая группа 1',
            slug='test-slug-1',
            description='Тестовое описание 1',
        )
        cls.post_1 = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group_1,
            image=cls.uploaded,
        )
        cls.comment = Comment.objects.create(
            post=cls.post_1,
            author=cls.user,
            text='Тестовый комментарий',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.guest_client = Client()

    # Проверяем используемые шаблоны
    def test_pages_use_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        page_names_templates = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': 'test-slug-1'}): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': 'Ivanov'}): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': f'{self.post_1.pk}'}):
                        'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': f'{self.post_1.pk}'}):
                        'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }
        for reverse_name, template in page_names_templates.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    # Проверяем контекст, передаваемый в шаблон каждой страницы
    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), 1)
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.author.username, 'Ivanov')
        self.assertEqual(first_object.text, 'Тестовый пост')
        self.assertEqual(first_object.pk, self.post_1.pk)
        self.assertEqual(first_object.group.slug, 'test-slug-1')
        self.assertEqual(first_object.image, 'posts/small.gif')

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = (self.authorized_client.get
                    (reverse('posts:group_list',
                             kwargs={'slug': 'test-slug-1'})))
        self.assertEqual(response.context['group'].title, 'Тестовая группа 1')
        self.assertEqual(response.context['group'].description,
                         'Тестовое описание 1')
        self.assertEqual(len(response.context['page_obj']), 1)
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.author.username, 'Ivanov')
        self.assertEqual(first_object.pk, self.post_1.pk)
        self.assertEqual(first_object.group.slug, 'test-slug-1')
        self.assertEqual(first_object.image, 'posts/small.gif')

    def test_author_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = (self.authorized_client.get
                    (reverse('posts:profile',
                             kwargs={'username': 'Ivanov'})))
        self.assertEqual(response.context['author'].username, 'Ivanov')
        self.assertEqual(response.context['counter'], 1)
        self.assertEqual(len(response.context['page_obj']), 1)
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, 'Тестовый пост')
        self.assertEqual(first_object.pk, self.post_1.pk)
        self.assertEqual(first_object.group.slug, 'test-slug-1')
        self.assertEqual(first_object.image, 'posts/small.gif')

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (self.authorized_client.
                    get(reverse('posts:post_detail',
                                kwargs={'post_id': f'{self.post_1.pk}'})))
        self.assertEqual(response.context.get('title'), 'Тестовый пост')
        self.assertEqual(response.context.get('author').username, 'Ivanov')
        self.assertEqual(response.context.get('post').text, 'Тестовый пост')
        self.assertEqual(response.context.get('post').group.title,
                         'Тестовая группа 1')
        self.assertEqual(response.context.get('post').image, 'posts/small.gif')
        self.assertEqual(response.context.get('counter'), 1)
        self.assertIsInstance(
            response.context.get('form').fields['text'],
            forms.fields.CharField
        )
        self.assertEqual(
            response.context.get('comments')[0].text,
            'Тестовый комментарий'
        )

    def test_create_page_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_edit_page_show_correct_context(self):
        """
        Шаблон create_post для post_edit сформирован
        с правильным контекстом.
        """
        response = (self.authorized_client.get
                    (reverse('posts:post_edit',
                             kwargs={'post_id': f'{self.post_1.pk}'})))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)
        self.assertTrue(response.context['is_edit'])

    # Проверяем, что пост с указанной группой отображается на нужных страницах
    def test_post_with_group_is_on_the_correct_pages(self):
        """
        Публикация с указанной группой отображается на главной странице,
        странице автора и странице этой группы
        """
        page_names = [
            reverse('posts:index'),
            reverse('posts:group_list',
                    kwargs={'slug': 'test-slug-1'}),
            reverse('posts:profile',
                    kwargs={'username': 'Ivanov'}),
        ]
        for reverse_name in page_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                post_0 = response.context['page_obj'].object_list[0]
                self.assertEqual(post_0, self.post_1)

    def test_post_with_group_is_not_on_the_other_group_page(self):
        """
        Публикация с указанной группой НЕ отображается
        на странице другой группы
        """
        self.group_2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug-2',
            description='Тестовое описание 2',
        )
        self.post_2 = Post.objects.create(
            author=self.user,
            text='Тестовый пост',
            group=self.group_2,
        )
        response = (self.authorized_client.get
                    (reverse('posts:group_list',
                             kwargs={'slug': 'test-slug-2'})))
        post_0 = response.context['page_obj'].object_list[0]
        self.assertNotEqual(post_0, self.post_1)

    # Проверяем кэширование главной страницы
    def test_cache_index_page(self):
        """Данные главной страницы сохраняются в кеше."""
        self.post_3 = Post.objects.create(
            author=self.user,
            text='Тестовый пост 3',
        )
        url = reverse('posts:index')
        cache.clear()
        content_0 = self.guest_client.get(url).content
        self.post_3.delete()
        content_1 = self.guest_client.get(url).content
        self.assertEqual(content_1, content_0)
        cache.clear()
        content_2 = self.guest_client.get(url).content
        self.assertNotEqual(content_2, content_1)


# Проверяем работу паджинатора
class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Ivanov')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        posts_qty = 14
        post_list = []
        for i in range(posts_qty):
            post_list.append(Post(
                author=self.user,
                text=f'Тестовый пост {i}',
                group=self.group,))
        Post.objects.bulk_create(post_list)

    def test_pages_contains_correct_qty_of_records(self):
        """
        Паджинатор отображает корректное кол-во постов
        на 1 и 2 страницах.
        """
        page_names = [
            reverse('posts:index'),
            reverse('posts:group_list',
                    kwargs={'slug': 'test-slug'}),
            reverse('posts:profile',
                    kwargs={'username': 'Ivanov'}),
        ]
        for reverse_name in page_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(len(response.context['page_obj']), 10)
                response = self.authorized_client.get(f'{reverse_name}?page=2')
                self.assertEqual(len(response.context['page_obj']), 4)


# Проверяем работу модуля подписок на авторов
class FollowersViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Ivanov')
        cls.author = User.objects.create_user(username='Petrov')
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост Петрова',
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)

    def test_user_can_follow_author(self):
        """
        Авториз. пользователь может подписаться на другого автора.
        """
        following = Follow.objects.filter(user=self.user, author=self.author)
        self.assertFalse(following.exists())
        self.authorized_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': f'{self.author}'})
        )
        self.assertTrue(following.exists())

    def test_user_cant_follow_himself(self):
        """
        Авториз. пользователь не может подписаться на самого себя.
        """
        self.authorized_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': f'{self.user}'})
        )
        following = Follow.objects.filter(user=self.user, author=self.user)
        self.assertFalse(following.exists())

    def test_unfollow_views(self):
        """
        Авториз. пользователь может отписаться от авторов,
        на которых подписан.
        """
        Follow.objects.create(
            user=self.user,
            author=self.author,
        )
        following = Follow.objects.filter(user=self.user, author=self.author)
        self.assertTrue(following.exists())
        self.authorized_client.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': f'{self.author}'})
        )
        self.assertFalse(following.exists())

    def test_follow_index_page(self):
        """
        Новая запись пользователя появляется в ленте тех,
        кто на него подписан и не появляется в ленте тех,
        кто не подписан.
        """
        self.new_post = Post.objects.create(
            author=self.author,
            text='Новый пост Петрова',
        )
        self.follow = Follow.objects.create(
            user=self.user,
            author=self.author,
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(
            response.context['page_obj'].object_list[0],
            self.new_post
        )
        # Проверяем отсутствие поста в ленте follow у автора поста
        # (т.к. он не может быть подписан сам на себя)
        response = self.authorized_author.get(
            reverse('posts:follow_index'))
        self.assertNotContains(response, 'Новый пост Петрова')
